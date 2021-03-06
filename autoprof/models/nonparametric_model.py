from .galaxy_model_object import Galaxy_Model
from .warp_model import Warp_Galaxy
from .parameter_object import Parameter_Array
from autoprof.utils.initialize import isophotes
from autoprof.utils.parametric_profiles import sersic
from autoprof.utils.conversions.coordinates import Rotate_Cartesian, coord_to_index, index_to_coord
import numpy as np
from scipy.stats import iqr
from scipy.optimize import minimize
from scipy.interpolate import UnivariateSpline

class NonParametric_Galaxy(Galaxy_Model):

    model_type = " ".join(("nonparametric", Galaxy_Model.model_type))
    parameter_specs = {
        "I(R)": {"units": "flux/arcsec^2"},
    }
    parameter_qualities = {
        "I(R)": {"form": "array", "loss": "radial loss", "regularize": "self", "regularize scale": 1},
    }

    def __init__(self, *args, **kwargs):
        if not hasattr(self, "profR"):
            self.profR = None
        super().__init__(*args, **kwargs)
        
    def build_parameters(self):
        super().build_parameters()
        for p in self.parameter_specs:
            if "(R)" not in p:
                continue
            if isinstance(self.parameter_specs[p], dict):
                self.parameters[p] = Parameter_Array(p, **self.parameter_specs[p])
            elif isinstance(self.parameter_specs[p], Parameter_Array):
                self.parameters[p] = self.parameter_specs[p]
            else:
                raise ValueError(f"unrecognized parameter specification for {p}")
            
    def set_window(self, *args, **kwargs):
        super().set_window(*args, **kwargs)

        if self.profR is None:
            self.profR = [0,1]
            while self.profR[-1] < np.sqrt(np.sum((self.window.shape/2)**2)):
                self.profR.append(max(1,self.profR[-1]*1.2))
            self.profR.pop()                
            self.profR = np.array(self.profR)
        
    def initialize(self, target = None):
        if target is None:
            target = self.target
        super().initialize(target)
        if self["I(R)"].value is not None:
            return
        target_area = target[self.window]
        icenter = coord_to_index(self["center"][0].value, self["center"][1].value, target_area)
        iso_info = isophotes(
            target_area.data,
            (icenter[1], icenter[0]),
            pa = self["PA"].value, q = self["q"].value,
            R = self.profR,
        )
        I = np.array(list(iso["flux"] for iso in iso_info)) / target.pixelscale**2
        S = np.array(list(iso["noise"]/np.sqrt(iso["N"]) for iso in iso_info)) / target.pixelscale**2
        self["I(R)"].set_value(I, override_fixed = True)
        self["I(R)"].set_uncertainty(np.clip(S, a_min = np.abs(I) * 1e-4, a_max = np.abs(I)), override_fixed = True)

    def compute_loss(self, data):
        # If the image is locked, no need to compute the loss
        if self.locked:
            return

        super().compute_loss(data)

        X, Y = data.loss_image.get_coordinate_meshgrid(self["center"][0].value, self["center"][1].value)
        if self.loss_speed_factor != 1:
            X = X[::self.loss_speed_factor,::self.loss_speed_factor]
            Y = Y[::self.loss_speed_factor,::self.loss_speed_factor]        
        X, Y = self.transform_coordinates(X, Y)
        R = self.radius_metric(X, Y)
        reg = self._regularize_loss()
        rad_bins = [self.profR[0]] + list((self.profR[:-1] + self.profR[1:])/2) + [self.profR[-1]*100]
            
        temp_loss = binned_statistic(R.ravel(), data.loss_image.data.ravel(), statistic = 'mean', bins = rad_bins)[0]
                            
        self.loss["radial loss"] = np.array(temp_loss)

        
    def radial_model(self, R, sample_image = None):
        if sample_image is None:
            sample_image = self.model_image        
        I = UnivariateSpline(self.profR, self["I(R)"].get_values() * sample_image.pixelscale**2, ext = "const", s = 0)
        return I(R)


class NonParametric_Warp(Warp_Galaxy):

    model_type = " ".join(("nonparametric", Warp_Galaxy.model_type))
    parameter_specs = {
        "I(R)": {"units": "flux/arcsec^2"},
    }
    parameter_qualities = {
        "I(R)": {"form": "array", "loss": "radial loss", "regularize": "self", "regularize scale": 1},
    }

    def initialize(self, target = None):
        if target is None:
            target = self.target
        super().initialize(target)
        if self["I(R)"].value is not None:
            return
            
        target_area = target[self.window]
        icenter = coord_to_index(self["center"][0].value, self["center"][1].value, target_area)
        iso_info = isophotes(
            target_area.data,
            (icenter[1], icenter[0]),
            pa = self["PA"].value, q = self["q"].value,
            R = self.profR,
        )
        I = np.array(list(iso["flux"] for iso in iso_info)) / target.pixelscale**2
        S = np.array(list(iso["noise"]/np.sqrt(iso["N"]) for iso in iso_info)) / target.pixelscale**2
        self["I(R)"].set_value(I, override_fixed = True)
        self["I(R)"].set_uncertainty(np.clip(S, a_min = np.abs(I) * 1e-4, a_max = np.abs(I)), override_fixed = True)
        
    def radial_model(self, R, sample_image = None):
        if sample_image is None:
            sample_image = self.model_image        
        I = UnivariateSpline(self.profR, self["I(R)"].get_values() * sample_image.pixelscale**2, ext = "const", s = 0)
        return I(R)

    def compute_loss(self, data):
        # If the image is locked, no need to compute the loss
        if self.locked:
            return

        super().compute_loss(data)

        X, Y = data.loss_image.get_coordinate_meshgrid(self["center"][0].value, self["center"][1].value)
        if self.loss_speed_factor != 1:
            X = X[::self.loss_speed_factor,::self.loss_speed_factor]
            Y = Y[::self.loss_speed_factor,::self.loss_speed_factor]
        X, Y = self.transform_coordinates(X, Y)
        R = self.radius_metric(X, Y)
        reg = self._regularize_loss()
        rad_bins = [self.profR[0]] + list((self.profR[:-1] + self.profR[1:])/2) + [self.profR[-1]*100]
            
        temp_loss = binned_statistic(R.ravel(), data.loss_image.data.ravel(), statistic = 'mean', bins = rad_bins)[0]
                            
        self.loss["radial loss"] = np.array(temp_loss)
