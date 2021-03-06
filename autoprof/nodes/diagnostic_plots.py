from flow import Process
from autoprof.utils.visuals import autocmap
from astropy.visualization import SqrtStretch, LogStretch, HistEqStretch
from astropy.visualization.mpl_normalize import ImageNormalize
import matplotlib.pyplot as plt
import os
import numpy as np

class Plot_Model(Process):
    """
    Plots the current model image.
    """

    def action(self, state):
        autocmap.set_under("k", alpha=0)
        plt.figure(figsize = (7, 7*state.data.model_image.shape[1]/state.data.model_image.shape[0]))
        plt.imshow(
            state.data.model_image.data,
            origin="lower",
            cmap=autocmap,
            norm=ImageNormalize(stretch=LogStretch(), clip=False),
        )
        plt.axis("off")
        plt.margins(0,0)
        plt.tight_layout()
        plt.savefig(
            os.path.join(
                state.options.plot_path,
                f"{self.name}_{state.options.name}_{state.models.iteration:04d}.jpg",
            ),
            dpi=state.options["ap_plotdpi", 800],
            bbox_inches = 'tight',
            pad_inches = 0
        )
        plt.close()

        residual = (state.data.target - state.data.model_image).data
        plt.figure(figsize = (7, 7*state.data.model_image.shape[1]/state.data.model_image.shape[0]))
        plt.imshow(
            residual,
            origin="lower",
            norm=ImageNormalize(stretch=HistEqStretch(residual), clip = False),
        )
        plt.axis("off")
        plt.margins(0,0)
        plt.tight_layout()
        plt.savefig(
            os.path.join(
                state.options.plot_path,
                f"{self.name}_Residual_{state.options.name}_{state.models.iteration:04d}.jpg",
            ),
            dpi=state.options["ap_plotdpi", 800],
            bbox_inches = 'tight',
            pad_inches = 0
        )
        plt.close()

        
        return state


class Plot_Loss_History(Process):
    """
    Plot the loss history for all the models to identify outliers.
    """

    def action(self, state):

        for model in state.models:
            if len(model.loss_history) == 0:
                continue
            for loss_quality in model.loss_history[0]:
                if isinstance(model.loss_history[0][loss_quality],float):
                    plt.plot(list(reversed(range(len(model.loss_history)))), np.log10(np.array(list(ml[loss_quality] for ml in model.loss_history)) / model.loss_history[-1][loss_quality]), label = f"{model.name}:{loss_quality}")
        plt.legend()
        plt.savefig(
            os.path.join(
                state.options.plot_path,
                f"{self.name}_{state.options.name}.jpg",
            ),
            dpi=state.options["ap_plotdpi", 500],
        )
        plt.close()
        
        return state
