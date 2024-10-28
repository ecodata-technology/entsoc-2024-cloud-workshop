from sympy import symbols, sin, Abs, pi, integrate, solve, lambdify
import numpy as np
import pandas as pd
import xarray as xra
import os
import zipfile
import urllib
import shutil
import sys
import geopandas as gpd
import rioxarray
from datetime import datetime, timedelta
from multiprocessing import Pool
import yaml


class DegreeDayCalculator:
    def __init__(self, lower_threshold, upper_threshold, method = 'single_sine'): 
        self.lt = lower_threshold
        self.ut = upper_threshold
        self.method = method
        self.methods = ['single_sine', 'simple_avg']

        if method not in self.methods:    
            print('Available degree day methods are:\n')
            for m in self.methods:
                print(f'{m}')
            raise ValueError(f'{method} is not an available degree day method.')

        self._initialize()

    def _initialize(self): 

        if self.method == 'single_sine':
            self._init_single_sine()
        elif self.method == 'simple_avg':
            self._init_simple_avg()

    def _init_single_sine(self):
        ### use sympy to create lambda functions for degday calcs
        # initialize symbols
        temp_min, temp_max, upp_thresh, low_thresh, t, l_bnd, u_bnd = symbols('temp_min temp_max upp_thresh low_thresh t l_bnd, u_bnd', real = True)

        ## single sin method
        # a sin curve with temp-range amplitude and 2-day period (2pi = 2)
        amp = (temp_max - temp_min) / 2
        sin_curve = amp * sin(2 * pi * t - (pi / 2)) + temp_min + amp
        self.sin_curve_fxn = lambdify([temp_min, temp_max, t], sin_curve, 'numpy')

        # definite integral wrt time t
        sin_intgr = integrate(sin_curve, (t, l_bnd, u_bnd))

        # values of t when sin(t) intersects lower threshold
        low_thresh_intersect = solve(sin_curve - low_thresh, t) 

        # values of t when sin(t) intersects upper threshold
        upp_thresh_intersect = solve(sin_curve - upp_thresh, t) 

        # integral of sin between intersections with lower threshold
        sin_low_intersect_intgr = (Abs(sin_intgr
                                    .subs(l_bnd, low_thresh_intersect[0])
                                    .subs(u_bnd, low_thresh_intersect[1])))

        # integral of sin between intersections with upper threshold
        sin_upp_intersect_intgr = (Abs(sin_intgr
                                    .subs(l_bnd, upp_thresh_intersect[0])
                                    .subs(u_bnd, upp_thresh_intersect[1])))

        # area of rectangle below lower threshold and between intersections low_thresh with sin
        low_intersect_rect = low_thresh * Abs(low_thresh_intersect[0] - low_thresh_intersect[1])

        # area of rectangle below upper threshold and between intersections of upp_thresh with sin
        upp_intersect_rect = upp_thresh * Abs(upp_thresh_intersect[0] - upp_thresh_intersect[1])

        # The cases
        # 1. upper threshold below temp_min 
        dd_case1_exp = upp_thresh - low_thresh
        self.dd_case1_fxn = lambdify([low_thresh, upp_thresh], dd_case1_exp, 'numpy')

        # 2. lower threshold above temp_max
        # dd = 0 hardcode

        # 3. upper threshold above temp_max, lower threshold below temp_min
        dd_case3_exp = sin_intgr.subs(l_bnd, 0).subs(u_bnd, 1) - low_thresh
        self.dd_case3_fxn = lambdify([temp_min, temp_max, low_thresh], dd_case3_exp, "numpy")

        # 4. upper threshold above temp_max, lower threshold above temp_min
        dd_case4_exp = sin_low_intersect_intgr - low_intersect_rect
        self.dd_case4_fxn = lambdify([temp_min, temp_max, low_thresh], dd_case4_exp, 'numpy')

        # 5. upper threshold below temp_max, lower threshold below temp_min
        dd_case5_exp = dd_case3_exp - sin_upp_intersect_intgr + upp_intersect_rect
        self.dd_case5_fxn = lambdify([temp_min, temp_max, low_thresh, upp_thresh], dd_case5_exp, 'numpy')

        # 6. upper threshold above temp_max, lower threshold above temp_min
        dd_case6_exp = dd_case4_exp - sin_upp_intersect_intgr + upp_intersect_rect
        self.dd_case6_fxn = lambdify([temp_min, temp_max, low_thresh, upp_thresh], dd_case6_exp, 'numpy')

        del temp_min, temp_max, upp_thresh, low_thresh, t, l_bnd, u_bnd
    
    def _init_simple_avg(self):
        
        pass 

    def get_degree_days(self, tmin, tmax):

        if (tmin >= tmax):
            print(f"warning: tmin ({tmin}) not less than tmax ({tmax}). returning nan.")
            return np.nan

        if self.lt >= self.ut: 
            print("warning: lower threshold not less than upper threshold. returning nan.")
            return np.nan

        if self.method == "single_sine":
            return self._get_ss_dd(tmin, tmax)
        elif self.method == "simple_avg":
            tavg = np.mean([tmin, tmax])
            return self._get_sa_dd(tavg)
        else: 
            print('Degree day method not yet implemented. Using single sine.')
            return self._get_ss_dd(tmin, tmax)

    
    def _get_ss_dd(self, tmin, tmax): # single sine
        
        if self.ut <= tmin: # case 1
            return self.ut - self.lt
        elif self.lt >= tmax: # case 2
            return 0
        elif self.ut >= tmax:
            if self.lt <= tmin: 
                return self.dd_case3_fxn(tmin, tmax, self.lt) # case 3
            else:
                return self.dd_case4_fxn(tmin, tmax, self.lt) # case 4
        else:
            if self.lt < tmin: 
                return self.dd_case5_fxn(tmin, tmax, self.lt, self.ut) # case 5
            else: 
                return self.dd_case6_fxn(tmin, tmax, self.lt, self.ut) # case 6

    def _get_sa_dd(self, tavg): # simple average
        
        if self.ut <= tavg: # case 1
            return self.ut - self.lt
        elif self.lt >= tavg: # case 2
            return 0
        else:
            return tavg - self.lt

    def get_degree_days_raster(self, tmin_array, tmax_array):

        # Initialize an empty array to store the result
        result_array = np.empty_like(tmin_array.values)
        # Loop over each cell of the grid and apply the custom function
        for i in range(result_array.shape[0]):
            for j in range(result_array.shape[1]):
                tmin = tmin_array.values[i, j]
                tmax = tmax_array.values[i, j]
                dd = self.get_degree_days(tmin, tmax) 
                result_array[i, j] = dd
       
        result_xra = xra.DataArray(result_array, dims=tmin_array.dims, coords=tmin_array.coords)

        return result_xra

def pull_PRISM_data(
    target_date: str, # e.g., '20240101'
    var_list: list, 
    prism_dir: str, 
    resolution: str = '800m', 
    overwrite: bool = False):
        
    # loop through climate variables 
    for var in var_list:
        print(f" Processing {var} Data")

        var_dir = os.path.join(prism_dir, target_date, var)
        var_file = os.path.join(var_dir, f'{target_date}_{var}.zip')
        
        if os.path.exists(var_file): 
            print(f'  Zip file for {var} on day = {target_date} already exists! Skipping download')
            continue

        # if os.path.exists(var_dir):
        #     if (overwrite == True):  
        #         shutil.rmtree(var_dir)
        #     else: 
        #         print("var_dir already exists! Specify overwrite argument = True.")
        #         sys.exit(1)
        os.makedirs(var_dir, exist_ok=True)

        # download data
        print('downloading prism data')
        if resolution == '800m': 
            base_url = 'https://services.nacse.org/prism/data/800m'
            url =f'{base_url}/{var}/{target_date}'
            urllib.request.urlretrieve(url, var_file)
            if not zipfile.is_zipfile(var_file):
               print('Data not found! Or too many downloads!') 
               return False

        # unzip data
        with zipfile.ZipFile(var_file, 'r') as zip_ref:
            zip_ref.extractall(var_dir)
        
    return True

def pull_PRISM_data_normals(
    target_day: str, # Jan 1 = '0101' 
    var_list: list, 
    prism_dir: str, 
    resolution: str = '800m', 
    overwrite: bool = False):
        
    # loop through climate variables 
    for var in var_list:
        print(f" Processing {var} Data")
        var_dir = os.path.join(prism_dir, target_day, var)
        var_file = os.path.join(var_dir, f'{target_day}_{var}.zip')

        if os.path.exists(var_file): 
            print(f'Zip file for {var} on day = {target_day} already exists! Skipping download')
            continue

        if os.path.exists(var_dir):
            if (overwrite == True):  
                shutil.rmtree(var_dir)
            else: 
                print("var_dir already exists! Specify overwrite argument = True.")
                return False
        os.makedirs(var_dir, exist_ok=True)

        # download data
        if resolution == '800m': 
            base_url = 'https://services.nacse.org/prism/data/public/normals/800m'
            url =f'{base_url}/{var}/{target_day}'
            urllib.request.urlretrieve(url, var_file)
            if not zipfile.is_zipfile(var_file):
               print('Data not found! Or too many downloads!') 
               return False

        # unzip data
        with zipfile.ZipFile(var_file, 'r') as zip_ref:
            zip_ref.extractall(var_dir)
        
    return True
    
def build_gdd_cube(
    prism_dir: str, 
    bbox_file: str,
    pest_params: dict,
    date_list: list = None, 
    start_date: datetime = None, 
    end_date: datetime = None,
    cube_out: str = None,
    resolution: str = '800m', 
):

    if date_list is None:
        if (start_date is None) | (end_date is None): 
            raise('No date list provided. Start and end dates required!')
        date_delta = (end_date - start_date).days
        date_list = [start_date + timedelta(i) for i in range(date_delta + 1)]
    else:
        if (start_date is not None) | (end_date is not None): 
            print('Date list provided by user. Ignoring start and end dates!')
        
    bbox = gpd.read_file(bbox_file)
    
    # loop through dates
    dd_cube = None
    for target_date_raw in date_list: 

        target_date = datetime.strftime(target_date_raw, '%Y%m%d')
        print(f'Pulling data for {target_date}')
        pull_succeeded = pull_PRISM_data(
            target_date, ['tmin', 'tmax'], prism_dir, 
            overwrite = False, resolution = resolution
            ) 
        print(f'PRISM Pull Succeeeded: {pull_succeeded}')
        if pull_succeeded == False: 
            print(f'!Failed to pull data for {target_date}')
            continue
        # prep tmin and tmax
        prism_dict = {} 
        for var in ['tmin', 'tmax']:
            # load var
            var_dir = os.path.join(prism_dir, target_date, var)
            raw_raster = rioxarray.open_rasterio(os.path.join(var_dir, f'prism_{var}_us_30s_{target_date}.bil'))
            or_raster = raw_raster.rio.clip(bbox.geometry, drop = True)
            or_raster = or_raster.where(or_raster != -9999)
            prism_dict[var] = or_raster.drop_vars('band').squeeze()
            del raw_raster, or_raster
        
        # loop pests and get gdds
        ss_calculator = DegreeDayCalculator(
            lower_threshold = pest_params['lt'], 
            upper_threshold = pest_params['ut'],
            method = pest_params['method']) 
        dd_array = ss_calculator.get_degree_days_raster(prism_dict['tmin'], prism_dict['tmax'])
        dd_array = dd_array.assign_coords(date=target_date_raw).expand_dims(date = 1)

        if dd_cube is None: 
            dd_cube = dd_array.copy()
        else: 
            dd_cube = xra.concat([dd_cube, dd_array], dim='date')

        if cube_out is not None:  
            dd_cube.to_netcdf(cube_out)

    return dd_cube 

def patch_gdd_cube(
   cube: xra.DataArray, 
   pest_params: dict,
   prism_dir: str, 
   bbox_file: str, 
   start_date: datetime = None, 
   end_date: datetime = None, 
   date_list: list = None, 
   overwrite: bool = False, 
   cube_out_file: str = None, 
):
    
    # get patch date list
    if date_list is None:
        if (start_date is None) | (end_date is None): 
            raise('No date list provided. Start and end dates required!')
        date_delta = (end_date - start_date).days
        date_list = [start_date + timedelta(i) for i in range(date_delta + 1)]
    else:
        if (start_date is not None) | (end_date is not None): 
            print('Date list provided by user. Ignoring start and end dates!')
    patch_date_set = set(date_list)
    patch_date_list = sorted(list(patch_date_set))

    # get cube dates
    cube_date_set = set(pd.to_datetime(cube.date.values))
    cube_date_list = sorted(list(cube_date_set))

    if overwrite: 

        # patches the whole date list 
        # will replace any dates already in the cube with newly computed layers
        print('Overwriting intersection between current cube and patch.')
        
        cube_patch = build_gdd_cube(
            date_list = patch_date_list,
            prism_dir = prism_dir, 
            bbox_file = bbox_file, 
            pest_params = pest_params,
        )

        rm_date_list = sorted(list(cube_date_set.intersection(patch_date_set)))
        cube_filtered = cube.sel(date = [x not in rm_date_list for x in cube_date_list])

        cube_patched = (
            xra.concat([cube_filtered, cube_patch], dim = 'date')
            .drop_duplicates(dim = 'date')
            .sortby('date')
        )

    else: 
        # only adds new dates not already in the cube 
        # useful for adding days to old cubes. 
        print('Skipping computation of intersecting dates.')

        new_date_list = sorted(list(patch_date_set.difference(cube_date_set)))
        cube_patch = build_gdd_cube(
            date_list = new_date_list, 
            prism_dir = prism_dir, 
            bbox_file = bbox_file, 
            pest_params = pest_params, 
        )

        cube_patched = (
            xra.concat([cube, cube_patch], dim = 'date')
            .drop_duplicates(dim='date')
            .sortby('date')
        )
    
    if cube_out_file is not None:  
        cube_patched.to_netcdf(cube_out_file)

    return cube_patched

def create_gdd_cube(
    start_date: datetime, 
    end_date: datetime,
    prism_dir: str, 
    gdd_dir: str,
    bbox_file: str,
    pest_params: dict,
    pest_list: list = None, 
    resolution: str = '800m', 
    overwrite: bool = False,
    parallel: bool = False,
):

    date_delta = (end_date - start_date).days
    date_list = [start_date + timedelta(i) for i in range(date_delta + 1)]
    bbox = gpd.read_file(bbox_file)
    if os.path.exists(gdd_dir):
        if (overwrite == True):  
            shutil.rmtree(gdd_dir)
        else: 
            print("gdd_dir already exists! Specify overwrite argument = True.")
            sys.exit(1)
    os.makedirs(gdd_dir)
    
    # loop through dates
    for target_date_raw in date_list: 

        target_date = datetime.strftime(target_date_raw, '%Y%m%d')
        print(f'Pulling data for {target_date}')
        pull_succeeded = pull_PRISM_data(
            target_date, ['tmin', 'tmax'], prism_dir, 
            overwrite = False, resolution = resolution
            ) 
        print(f'PRISM Pull Succeeeded: {pull_succeeded}')
        if pull_succeeded == False: 
            print(f'!Failed to pull data for {target_date}')
            continue
        # prep tmin and tmax
        prism_dict = {} 
        for var in ['tmin', 'tmax']:
            # load var
            var_dir = os.path.join(prism_dir, target_date, var)
            raw_raster = rioxarray.open_rasterio(os.path.join(var_dir, f'prism_{var}_us_30s_{target_date}.bil'))
            or_raster = raw_raster.rio.clip(bbox.geometry, drop = True)
            or_raster = or_raster.where(or_raster != -9999)
            prism_dict[var] = or_raster.drop_vars('band').squeeze()
            del raw_raster, or_raster
        
        # loop pests and get gdds
        if pest_list is None:
            pest_list = list(pest_params.keys())
        for pest in pest_list:

            print(f'Calculating GDD raster for {pest}')
            ss_calculator = DegreeDayCalculator(
                lower_threshold = pest_params[pest]['lt'], 
                upper_threshold = pest_params[pest]['ut'],
                method = pest_params[pest]['method']) 
            dd_array = ss_calculator.get_degree_days_raster(prism_dict['tmin'], prism_dict['tmax'])
            dd_array = dd_array.assign_coords(date=target_date_raw).expand_dims(date = 1)
            # dd_dataset = dd_array.to_dataset(name = target_date)

            cube_file = os.path.join(gdd_dir, f'gdd_cube_{pest}.nc')
            write_mode = 'w'
            if not os.path.isfile(cube_file): 
                # write_mode = 'a' # append in place 
                dd_array.to_netcdf(cube_file, mode = write_mode)
            else: 
                dd_base = xra.load_dataarray(cube_file)
                dd_array = xra.concat([dd_base, dd_array], dim='date')
                dd_array.to_netcdf(cube_file, mode = write_mode)

    return True
            
def create_gdd_cube_normals( # for daily normals
    start_date: datetime, # use year of comparison to ensure leap day is included / excluded
    end_date: datetime,
    prism_dir: str, 
    gdd_dir: str,
    bbox_file: str,
    pest_params: dict,
    pest_list: list = None, 
    resolution: str = '800m', 
    overwrite: bool = False,
    agg_to_layer: bool = False,
    layer_file_ext: str = 'nc', 
):

    date_delta = (end_date - start_date).days
    date_list = [start_date + timedelta(i) for i in range(date_delta + 1)]
    bbox = gpd.read_file(bbox_file)
    if os.path.exists(gdd_dir):
        if (overwrite == True):  
            shutil.rmtree(gdd_dir)
        else: 
            print("gdd_dir already exists! Specify overwrite argument = True.")
            sys.exit(1)
    os.makedirs(os.path.join(gdd_dir, 'cubes'))
    
    # loop through dates
    for target_date_raw in date_list: 

        # target_date = datetime.strftime(target_date_raw, '%Y%m%d')
        target_day = str(target_date_raw.month).zfill(2) + str(target_date_raw.day).zfill(2)
        print(f'Pulling data for {target_day}')
        pull_succeeded = pull_PRISM_data_normals(
            target_day, ['tmin', 'tmax'], prism_dir, 
            overwrite = overwrite, resolution = resolution
            ) 
        print(f'PRISM Pull Succeeeded: {pull_succeeded}')
        if pull_succeeded == False: 
            print(f'!Failed to pull data for {target_day}')
            continue
        # prep tmin and tmax
        prism_dict = {} 
        for var in ['tmin', 'tmax']:
            # load var
            var_dir = os.path.join(prism_dir, target_day, var)
            raw_raster = rioxarray.open_rasterio(os.path.join(var_dir, f'PRISM_{var}_30yr_normal_800mD1_{target_day}_bil.bil'))
            or_raster = raw_raster.rio.clip(bbox.geometry, drop = True)
            or_raster = or_raster.where(or_raster != -9999)
            prism_dict[var] = or_raster.drop_vars('band').squeeze()
            del raw_raster, or_raster
        
        # loop pests and get gdds
        if pest_list is None:
            pest_list = list(pest_params.keys())
        if not isinstance(pest_list, list): pest_list = [pest_list]
        for pest in pest_list:
            print(f'Calculating GDD raster for {pest}')
            ss_calculator = DegreeDayCalculator(
                lower_threshold = pest_params[pest]['lt'], 
                upper_threshold = pest_params[pest]['ut'],
                method = pest_params[pest]['method']) 
            dd_array = ss_calculator.get_degree_days_raster(prism_dict['tmin'], prism_dict['tmax'])
            dd_array = dd_array.assign_coords(date=target_date_raw).expand_dims(date = 1)
            # dd_dataset = dd_array.to_dataset(name = target_day)

            # concatenate and write to NetCDF
            cube_file = os.path.join(gdd_dir, 'cubes', f'gdd_cube_normals_{pest}.nc')
            write_mode = 'w'
            if not os.path.isfile(cube_file): 
                # write_mode = 'a' # append in place 
                dd_array.to_netcdf(cube_file, mode = write_mode)
            else: 
                dd_base = xra.load_dataarray(cube_file)
                dd_array = xra.concat([dd_base, dd_array], dim='date')
                dd_array.to_netcdf(cube_file, mode = write_mode)
            
            if agg_to_layer:

                print(f'Aggregating cube for {pest} to {target_day}')
                layer_dirs = [os.path.join(gdd_dir, 'layers', pest, 'leap_year'), os.path.join(gdd_dir, 'layers', pest, 'norm_year')]
                for layer_dir, leap_ind, leap_char in zip(layer_dirs, [True, False], ['leapyear_', '']): 
                   
                    print(f'Directory: {layer_dir}')
                    print(f'Is leap year?: {leap_ind}')
                    print(f'File string: {leap_char}')
                    if (not leap_ind) & (target_day == '0229'): 
                        print('Skipping leap day!')
                        continue # skip aggregation for leap day

                    layer_file = os.path.join(layer_dir, f'gdd_normal_layer_{leap_char}{pest}_{target_day}.{layer_file_ext}')
                    if not os.path.exists(layer_dir):
                        print(f'Creating directory {layer_dir}')
                        os.makedirs(layer_dir)
                    if (os.path.exists(layer_file)): 
                        if overwrite:
                            print(f'Removing file {layer_file}')
                            os.remove(layer_file)
                        else: raise('Layer file already exists. Set overwrite = True')
                   
                    exclude_days = None
                    if not leap_ind: 
                        exclude_days = ['02-29']
                        print(f'Excluding {exclude_days} from aggregation')
                    dd_layer = aggregate_cube_by_date(
                        cube = dd_array, 
                        start_day = pest_params[pest]['start_date'], 
                        end_day = str(target_date_raw.month) + '-' + str(target_date_raw.day), 
                        exclude_days = exclude_days
                    )

                    if layer_file_ext == 'nc': 
                        dd_layer.to_netcdf(layer_file)
                    else: raise('File extension not supported! NetCDF only right now.')

def aggregate_cube_by_date(
    cube: xra.DataArray, 
    exclude_day: str = None, # eg leap day: ['02-29']
    start_day: str = '01-01', # must be in this format
    end_day: str = '12-31',
): 

    # get / use biofix date
    biofix_mon_day = [int(x) for x in start_day.split('-')]
    biofix_date = pd.to_datetime(datetime(2024, biofix_mon_day[0], biofix_mon_day[1]))
    end_mon_day = [int(x) for x in end_day.split('-')]
    end_date = pd.to_datetime(datetime(2024, end_mon_day[0], end_mon_day[1]))
    if exclude_day is not None: 
        exclude_mon_day = [int(x) for x in exclude_day.split('-')]
        exclude_date = pd.to_datetime(datetime(2024, exclude_mon_day[0], exclude_mon_day[1]))
    else: exclude_date = pd.to_datetime(datetime(2023, 1, 1)) 

    # print(cube)
    max_date = cube.date.values.max()
    dd_layer = (
        cube.sel(date = (cube.date >= biofix_date) & (cube.date <= end_date) & (cube.date != exclude_date))
        .sum(dim='date')
        .assign_coords(date = max_date)
        .expand_dims(date = 1)
    )
    return  dd_layer

def aggregate_cube_to_timeseries(
    cube: xra.DataArray
):

    gdd = cube.mean(dim=['x', 'y']).values
    dates = cube.date.values
    df = (
        pd.DataFrame({'date': dates, 'gdd_mean': gdd})
        .assign(
            gdd_cum = lambda x: x.gdd_mean.cumsum()
        )
    )

    return df

if __name__ == "__main__":

    # tmin = 5
    # tmax = 15
    # lt = 0
    # ut = 20

    # ss_calculator = DegreeDayCalculator(lt, ut)
    # print(ss_calculator.method)
    # degday = ss_calculator.get_degree_days(tmin, tmax)
    # print(degday)

    # pull_PRISM_data(
    #     target_date = '20240101', 
    #     var_list = ['tmin', 'tmax'], 
    #     prism_dir = '/home/ec2-user/repos/usda-ars-dorman-cdd-app-shiny/data/prism/800m/2024', 
    #     resolution = '800m', 
    #     overwrite = False
    #     ) 

    # tmin_array = rioxarray.open_rasterio('/home/ec2-user/repos/usda-ars-dorman-cdd-app-etl/data/prism/degday_test_rasters/PRISM_tmin_early_4kmD2_20240127_bil.bil_or.tif')
    # tmin_array = tmin_array.where(tmin_array != -9999)
    # tmax_array = rioxarray.open_rasterio('/home/ec2-user/repos/usda-ars-dorman-cdd-app-etl/data/prism/degday_test_rasters/PRISM_tmax_early_4kmD2_20240127_bil.bil_or.tif')
    # tmax_array = tmax_array.where(tmax_array != -9999)

    # result_array = ss_calculator.get_degree_day_raster(tmin_array, tmax_array)
    # print(result_array) 

    dd = xra.load_dataarray('/home/ec2-user/repos/usda-ars-dorman-cdd-app-shiny/data/gdd/init-cubes/gdd_cube_black_cutworm.nc')
    dates_prefilter = pd.to_datetime(dd.date.values) < pd.to_datetime(datetime(2024, 1, 5))
    dd = dd.sel(date = dates_prefilter)
    print(dd.date.values)
    with open('/home/ec2-user/repos/usda-ars-dorman-cdd-app-shiny/data/pest_params.yaml') as f: 
        pest_params = yaml.safe_load(f)
    bc_params = {'lt': 0, 'ut': 36, 'method': 'single_sine'}
    bbox = '/home/ec2-user/repos/usda-ars-dorman-cdd-app-shiny/data/or-bbox.geojson'
    prism_dir = '/home/ec2-user/repos/usda-ars-dorman-cdd-app-shiny/data/prism/800m/2024'
    print(bc_params)

    cube_patched_no_overwrite = patch_gdd_cube(
        cube = dd, 
        pest_params = bc_params, 
        prism_dir = prism_dir, 
        bbox_file = bbox, 
        start_date = datetime(2024, 1, 3), 
        end_date = datetime(2024, 1, 6), 
        overwrite = False
    )

    print(cube_patched_no_overwrite.date.values)
    print(f'sum of vals for no overwrite: {cube_patched_no_overwrite.sum()}')

    cube_patched_overwrite = patch_gdd_cube(
        cube = dd, 
        pest_params = bc_params, 
        prism_dir = prism_dir, 
        bbox_file = bbox, 
        start_date = datetime(2024, 1, 5), 
        end_date = datetime(2024, 1, 6), 
        overwrite = True
    )

    print(cube_patched_overwrite.date.values)
    print(f'sum of vals for overwrite: {cube_patched_overwrite.sum()}')