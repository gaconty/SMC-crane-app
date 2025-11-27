"""
MODULE 1: ADVANCED MESH GENERATOR (CORE ONLY)
Chức năng: Rời rạc hóa tấm lót và mô phỏng đặc tính địa chất.
"""

import numpy as np
from matplotlib.path import Path # Vẫn cần Path để tính toán hình học (Point-in-Polygon)

class AdvancedMeshGenerator:
    def __init__(self, mesh_size=0.1):
        self.mesh_size = mesh_size
        self.nodes_X = None       
        self.nodes_Y = None       
        self.Ks_matrix = None     
        self.active_mask = None   
        self.dA = 0               
        self.bounds = {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 0}

    def create_rectangular_mesh(self, L, W, default_Ks=5000):
        vertices = [
            (-L/2, -W/2), (L/2, -W/2), (L/2, W/2), (-L/2, W/2)
        ]
        self.create_polygon_mesh(vertices, default_Ks)

    def create_polygon_mesh(self, vertices, default_Ks=5000):
        verts = np.array(vertices)
        self.bounds['min_x'], self.bounds['max_x'] = np.min(verts[:, 0]), np.max(verts[:, 0])
        self.bounds['min_y'], self.bounds['max_y'] = np.min(verts[:, 1]), np.max(verts[:, 1])

        padding = self.mesh_size * 2
        x_range = np.arange(self.bounds['min_x'] - padding, self.bounds['max_x'] + padding, self.mesh_size)
        y_range = np.arange(self.bounds['min_y'] - padding, self.bounds['max_y'] + padding, self.mesh_size)
        
        self.nodes_X, self.nodes_Y = np.meshgrid(x_range, y_range)
        self.dA = self.mesh_size ** 2

        points_flat = np.vstack((self.nodes_X.flatten(), self.nodes_Y.flatten())).T
        poly_path = Path(vertices)
        mask_flat = poly_path.contains_points(points_flat)
        
        self.active_mask = mask_flat.reshape(self.nodes_X.shape)
        
        self.Ks_matrix = np.zeros_like(self.nodes_X)
        self.Ks_matrix[self.active_mask] = default_Ks

    def modify_soil_property(self, shape_type, params, new_Ks):
        if self.nodes_X is None: return

        mask_modif = None
        if shape_type == 'circle':
            dist = np.sqrt((self.nodes_X - params['x'])**2 + (self.nodes_Y - params['y'])**2)
            mask_modif = (dist <= params['r'])
        elif shape_type == 'rect':
            mask_modif = (self.nodes_X >= params['x_min']) & (self.nodes_X <= params['x_max']) & \
                         (self.nodes_Y >= params['y_min']) & (self.nodes_Y <= params['y_max'])

        final_mask = mask_modif & self.active_mask
        self.Ks_matrix[final_mask] = new_Ks

    def get_mesh_data(self):
        return {
            'X': self.nodes_X, 'Y': self.nodes_Y,
            'Ks': self.Ks_matrix, 'Active': self.active_mask,
            'dA': self.dA, 'mesh_size': self.mesh_size
        }