import os
import shutil
import datetime
import csv
import shapefile
import imageio
import numpy as np
import matplotlib.pyplot as plt

for path in [
    'display',
    'display/temp',
    'display/footprint']:
    if os.path.exists(path) == False:
        os.mkdir(path)

def read_dmp_data(path):
    data = {}
    with open(path) as f:
        for uuid, start_time, hour, duration, visit_type, lat, lon in csv.reader(f):
            if uuid != 'id':
                if uuid not in data:
                    data[uuid] = []
                data[uuid].append([
                    datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S'),
                    float(lat),
                    float(lon)])
    
    for uuid in list(data):
        data[uuid].sort()
    
    return data

def footprint2matrix(footprint):
    matrix = [[None for j in range(192)] for i in range((footprint[-1][0].date() - footprint[0][0].date()).days+1)]

    for start_time, lat, lon in footprint:
        row = (start_time.date() - footprint[0][0].date()).days
        col = int((start_time - start_time.replace(hour=0, minute=0)).total_seconds()/(15*60))

        matrix[row][col] = lat
        matrix[row][col+96] = lon

    _, pervious_lat, pervious_lon = footprint[0]

    for row in range(len(matrix)):
        for col in range(96):
            if matrix[row][col] == None:
                matrix[row][col] = pervious_lat
                matrix[row][col+96] = pervious_lon
            else:
                pervious_lat = matrix[row][col]
                pervious_lon = matrix[row][col+96]
    
    return np.array(matrix, dtype=float)

def matrix2foorprint(matrix):
    footprint = []

    if len(matrix.shape) == 1:
        matrix = matrix.reshape(1, -1)

    for row in range(matrix.shape[0]):
        for col in range(96):
            footprint.append([
                datetime.datetime(2023,4,1)+datetime.timedelta(days=row, minutes=col*15),
                matrix[row, col],
                matrix[row, col+96]
            ])
    
    return footprint

class footprint_display:
    def __init__(self):
        self.MAP_SIZE_COEFFICIENT = 0.5
        self.DISPLAY_TAIL_LEN = 20
        shape = shapefile.Reader("resource/shapefiles/idn_admbnda_adm1_bps_20200401.shp")

        self.border_list = []
        
        for shapeRecord in shape.shapeRecords():
            area = shapeRecord.shape.__geo_interface__['coordinates']
            for borders in area:
                if type(borders[0]) == tuple:
                    self.border_list.append([[i[0] for i in borders], [i[1] for i in borders]])
                else:
                    for border in borders:
                        self.border_list.append([[i[0] for i in border], [i[1] for i in border]])

        self.latlon_range = {
            'lat':{
                'max':max([max(border[1]) for border in self.border_list]), 
                'min':min([min(border[1]) for border in self.border_list])}, 
            'lon':{
                'max':max([max(border[0]) for border in self.border_list]),
                'min':min([min(border[0]) for border in self.border_list])}}
        self.latlon_range['area'] = (self.latlon_range['lat']['max']-self.latlon_range['lat']['min'])*\
                                    (self.latlon_range['lon']['max']-self.latlon_range['lon']['min'])

    def plot_map(self, matrix, img_name, interval = 1, fix_map = True):
        if os.path.exists(os.path.join("display", "temp", img_name)):
            shutil.rmtree(os.path.join("display", "temp", img_name))
        os.mkdir(os.path.join("display", "temp", img_name))

        if len(matrix.shape) == 1:
            matrix = matrix.reshape(1, -1)
        
        lat_matrix, lon_matrix = matrix[:, :96], matrix[:, 96:]

        if fix_map:
            latlon_range = self.latlon_range
            MAP_SIZE = 1 * self.MAP_SIZE_COEFFICIENT
        else:
            latlon_range = {
                'lat':{'max':np.max(lat_matrix), 'min':np.min(lat_matrix)},
                'lon':{'max':np.max(lon_matrix), 'min':np.min(lon_matrix)},
                'area':(np.max(lat_matrix)-np.min(lat_matrix))*(np.max(lon_matrix)-np.min(lon_matrix))}
            MAP_SIZE = self.MAP_SIZE_COEFFICIENT*(self.latlon_range['area']/latlon_range['area'])**0.5

        for col in range(0, 96, interval):
            plt.figure(figsize=(
                (latlon_range['lon']['max']-latlon_range['lon']['min'])*MAP_SIZE, 
                (latlon_range['lat']['max']-latlon_range['lat']['min'])*MAP_SIZE))
            plt.plot()
            for row in range(matrix.shape[0]):
                plt.scatter(
                    lon_matrix[row, max(0, col-self.DISPLAY_TAIL_LEN):col].tolist(),
                    lat_matrix[row, max(0, col-self.DISPLAY_TAIL_LEN):col].tolist())
                plt.plot(
                    lon_matrix[row, max(0, col-self.DISPLAY_TAIL_LEN):col].tolist(),
                    lat_matrix[row, max(0, col-self.DISPLAY_TAIL_LEN):col].tolist())

            for coor_X, coor_Y in self.border_list:
                plt.plot(coor_X, coor_Y)

            plt.xlim([latlon_range['lon']['min'], latlon_range['lon']['max']])
            plt.ylim([latlon_range['lat']['min'], latlon_range['lat']['max']])
            plt.text(
                latlon_range['lon']['min'],
                latlon_range['lat']['min'],
                (datetime.datetime(2023,4,1)+datetime.timedelta(minutes=col*15)).strftime("%H:%M:%S"),
                fontdict={'size':20, 'color':'red'})
            plt.savefig(os.path.join("display", "temp", img_name, f"{col}.png"))
            plt.close()

        images = []
        for root_img, folder_img, files_img in os.walk(os.path.join("display", "temp", img_name)):
            for file_img in files_img:
                images.append([int(file_img.replace(".png", "")), imageio.v3.imread(os.path.join(root_img,file_img))])

        images.sort()
        images = [i[1] for i in images]
        imageio.mimsave(os.path.join("display", "footprint", f"{img_name}.gif"), images, duration=0.1)
        shutil.rmtree(os.path.join("display", "temp", img_name))
        
        
            

    
            
