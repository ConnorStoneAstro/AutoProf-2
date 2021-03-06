import numpy as np
from .parameter_object import Parameter, Parameter_Array
from autoprof.utils.conversions.coordinates import coord_to_index, index_to_coord
from autoprof.image import Model_Image, AP_Window
from copy import deepcopy

def _set_default_parameters(self):
    self._base_window = None
    self.parameters = {}
    self.loss = None
    self.iteration = -1
    self.is_sampled = False
    self.is_convolved = False
    self.is_integrated = False
    self.model_integrate = None
    self.integrate_window = None

def set_target(self, target):
    self.target = target

def set_window(self, window = None, index_units = True):
    # If no window given, use the whole image
    if window is None:
        window = [
            [0, self.target.shape[0]],
            [0, self.target.shape[1]],
        ]
        index_units = False

    # If the window is given in proper format, simply use as-is
    if isinstance(window, AP_Window):
        self.window = window
    elif index_units:# If window is given as list-of-list format
        self.window = AP_Window(
            self.target.origin + np.array((window[1][0],window[0][0]))*self.target.pixelscale,
            np.array((window[1][1] - window[1][0], window[0][1] - window[0][0]))*self.target.pixelscale,
        )
    else:
        self.window = AP_Window(
            self.target.origin + np.array((window[1][0],window[0][0])),
            np.array((window[1][1] - window[1][0], window[0][1] - window[0][0])),
        )
    if self._base_window is None:
        self._base_window = self.window
        
    # Create the model image for this model
    self.model_image = Model_Image(
        np.zeros(np.round(self.window.shape / self.target.pixelscale).astype(int)),
        pixelscale = self.target.pixelscale,
        origin = self.window.origin,
    )
 
def scale_window(self, scale):
    self.set_window(self._base_window.scaled_window(scale, limit_window = self.target.window))

def update_locked(self, locked):
    if isinstance(locked, bool):
        self.locked = bool(self.user_locked) or locked
    elif isinstance(locked, int):
        if self.user_locked is not None:
            self.locked = self.user_locked
            return
        if locked <= 0:
            self.locked = False
        else:
            self.locked = locked
    else:
        raise ValueError(f"Unrecognized lock type: {type(locked)}")

@classmethod
def build_parameter_specs(cls, user_specs = None):
    parameter_specs = {}
    for base in cls.__bases__:
        try:
            parameter_specs.update(base.build_parameter_specs())
        except AttributeError:
            pass
    parameter_specs.update(cls.parameter_specs)
    if user_specs is not None:
        for p in user_specs:
            # If the user supplied a parameter object subclass, simply use that as is
            if isinstance(user_specs[p], Parameter):
                parameter_specs[p] = user_specs[p]
            else: # if the user supplied parameter specifications, update the defaults
                parameter_specs[p].update(user_specs[p])        
    return parameter_specs

@classmethod
def build_parameter_qualities(cls):
    parameter_qualities = {}
    for base in cls.__bases__:
        try:
            parameter_qualities.update(base.build_parameter_qualities())
        except AttributeError:
            pass
    parameter_qualities.update(cls.parameter_qualities)
    return parameter_qualities

def build_parameters(self):
    for p in self.parameter_specs:
        if isinstance(self.parameter_specs[p], dict):
            self.parameters[p] = Parameter(p, **self.parameter_specs[p])
        elif isinstance(self.parameter_specs[p], Parameter):
            self.parameters[p] = self.parameter_specs[p]
        else:
            raise ValueError(f"unrecognized parameter specification for {p}")

def step_iteration(self):
    if self.locked:
        if isinstance(self.locked, int):
            self.update_locked(self.locked - 1)
        return
    # Add a new set of parameters to the history that defaults to the most recent values
    if not self.loss is None:
        self.history.add_step(self.parameters, self.loss)
        self.loss = None
    self.iteration += 1
    self.is_sampled = False
    self.is_convolved = False
    self.is_integrated = False

def save_model(self, fileobject):
    fileobject.write("\n" + "\n" + "*"*70 + "\n")
    fileobject.write(self.name + "\n")
    fileobject.write("*"*70 + "\n")
    for p in self.parameters:
        fileobject.write(f"{str(self.parameters[p])}\n")

def __getitem__(self, key):

    # Try to access the parameter by name
    if key in self.parameters:
        return P[key]

    # Check any parameter arrays for the key
    for subpar in self.parameters.values():
        if not isinstance(subpar, Parameter_Array):
            continue
        try:
            return subpar[key]
        except KeyError:
            pass
        
    raise KeyError(f"{key} not in {self.name}. {str(self)}")
