from .substate_object import SubState
from autoprof.models import BaseModel
from autoprof.pipeline.class_discovery import all_subclasses
import numpy as np
import matplotlib.pyplot as plt
import os

class Models_State(SubState):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.models = {}
        self.model_list = []
        self.iteration = -1
        
    def add_model(self, name, model, **kwargs):
        MODELS = all_subclasses(BaseModel)
        if not "window" in kwargs:
            kwargs["window"] = self.state.data.target.window
        if isinstance(model, str):
            for m in MODELS:
                if m.model_type == model:
                    self.models[name] = m(name, target = self.state.data.target, **kwargs)
                    break
        elif isinstance(model, BaseModel):
            self.models[name] = model(name, target = self.state.data.target, **kwargs)
        else:
            raise ValueError('model should be a string or AutoProf Model object, not: {type(model)}')

        self.model_list.append(name)
        self.organize_model_list()
        
    def organize_model_list(self):
        model_sizes = list(-np.prod(self.models[m].window.shape) for m in self.model_list)
        N = np.argsort(model_sizes)
        new_list = []
        for n in N:
            new_list.append(self.model_list[n])
        self.model_list = new_list
            
    def initialize(self, target):
        for m in self.model_list:
            self.models[m].initialize(target)

    def compute_loss(self):        
        for m in self.model_list:
            self.models[m].compute_loss(self.state.data)

    def sample_models(self):
        for m in self.model_list:
            # Don't bother resampling the model if nothing has been updated
            if self.models[m].is_sampled:
                continue
            self.models[m].sample_model()

    def integrate_models(self):
        for m in self.model_list:
            if self.models[m].is_integrated:
                continue
            self.models[m].integrate_model()

    def convolve_psf(self):
        for m in self.model_list:
            # Don't bother convolving the model if nothing has been updated
            if self.models[m].is_convolved:
                continue
            self.models[m].convolve_psf()

    def add_integrated_models(self):
        for m in self.model_list:
            self.models[m].add_integrated_model()

    def step_iteration(self):
        self.iteration += 1
        print('Now on iteration: ', self.iteration)
        for m in self.model_list:
            self.models[m].step_iteration()

    def unlock_models(self):
        for m in self.model_list:
            self.models[m].update_locked(False)

    def save_models(self):
        with open(os.path.join(self.state.options.save_path, self.state.options.name + '.txt'), "w") as f:
            for m in self.model_list:
                self.models[m].save_model(f)
            
    def __iter__(self):
        self._iter_model = -1
        return self

    def __next__(self):
        self._iter_model += 1
        if self._iter_model < len(self.model_list):
            return self.models[self.model_list[self._iter_model]]
        else:
            raise StopIteration
