"""Account for linear repulsive term from overlap."""

from dataclasses import dataclass
import numpy as np
from scipy import signal
from scipy import integrate
from scipy import optimize
import warnings
from pprint import pprint
import mpmath as mp
from flint import acb, arb, ctx
from catchemi import NewnsAndersonNumerical

class FitParametersNewnsAnderson:

    def __init__(self, **kwargs):
        """Here we convert everything into numpy arrays."""
        self.Vsd = kwargs.get('Vsd', None)
        self.width = kwargs.get('width', None)
        self.eps_a = kwargs.get('eps_a', None)
        self.eps_sp_max = kwargs.get('eps_sp_max', None)
        self.eps_sp_min = kwargs.get('eps_sp_min', None)
        self.Delta0_mag = kwargs.get('Delta0_mag', None)
        self.precision = kwargs.get('precision', None)
        self.verbose = kwargs.get('verbose', False)
        self.eps = kwargs.get('eps', None)

        self.validate_inputs()
        
    def validate_inputs(self):
        """Check if everything is the same length and
        has the right value."""
        assert self.Vsd != None, "Vsd is not defined."
        assert self.width != None, "width is not defined."
        assert self.eps_a != None, "eps_a is not defined."

        assert len(self.Vsd) == len(self.width)

        # The following default values are
        # to be set if not provided and are
        # constant for all metals.
        if self.eps_sp_max == None: 
            self.eps_sp_max = 15
        if self.eps_sp_min == None: 
            self.eps_sp_min = -15
        if self.Delta0_mag == None:
            self.Delta0_mag = 0.0
        if self.precision == None: 
            self.precision = 50

    def fit_parameters(self, args, eps_ds) -> np.ndarray:
        """Fit parameters of alpha, beta and constant offset
        of the NewnsAndersonModel including repulsive interations
        to DFT energies."""

        alpha, beta, constant_offset = args
        # Make sure that all the quantities are positive
        # Constant offset can be any sign
        alpha = abs(alpha)
        beta = abs(beta)

        # Determine the chemisorption energy for the 
        # materials for which we have eps_d values
        chemi_energy = []
        for i, eps_d in enumerate(eps_ds):
            Vsd = self.Vsd[i]
            width = self.width[i]

            # Get the chemisorption energy for each 
            # epsilon_d value
            chemisorption = NewnsAndersonLinearRepulsion(
                Vsd = Vsd,
                eps_a = self.eps_a,
                eps_d = eps_d,
                width = width,
                eps = self.eps,
                Delta0_mag = self.Delta0_mag,
                eps_sp_max=self.eps_sp_max,
                eps_sp_min=self.eps_sp_min,
                precision=self.precision,
                verbose=self.verbose,
                alpha=alpha,
                beta=beta,
                constant_offset=constant_offset,
                )
            chemi_energy.append(chemisorption.get_chemisorption_energy())

        chemi_energy = np.array(chemi_energy) 

        # Write out the parameters
        if self.verbose:
            print("alpha:", alpha)
            print("beta:", beta)
            print("constant_offset:", constant_offset)
            print("")

        return chemi_energy


class NewnsAndersonLinearRepulsion(NewnsAndersonNumerical):
    """Class that provides the Newns-Anderson hybridisation
    energy along with the linear orthogonalisation energy.
    It subclasses NewnsAndersonNumerical for the Hybridisation
    energy and adds the orthogonalisation penalty separately."""

    def __init__(self, Vsd, eps_a, eps_d, width, eps, 
                 Delta0_mag=0.0, eps_sp_max=15, eps_sp_min=-15,
                 precision=50, verbose=False,
                 alpha=0.0, beta=0.0, constant_offset=0.0):
        Vak = np.sqrt(beta) * Vsd
        super().__init__(Vak, eps_a, eps_d, width, 
                         eps, Delta0_mag, eps_sp_max,
                         eps_sp_min, precision, verbose)
        self.alpha = alpha
        self.beta = beta
        self.constant_offset = constant_offset

        # The goal is to find the chemisorption energy
        self.chemisorption_energy = None
        # Also store the orthogonalisation energy
        self.orthogonalisation_energy = None
    
    def get_chemisorption_energy(self):
        """Utility function for returning 
        the chemisorption energy."""
        if self.verbose:
            print('Computing the chemisorption energy...')
        if self.chemisorption_energy is not None:
            return self.chemisorption_energy
        else:
            self.compute_chemisorption_energy()
            return float(self.chemisorption_energy)
    
    def get_orthogonalisation_energy(self):
        """Utility function for returning 
        the orthogonalisation energy."""
        if self.verbose:
            print('Computing the orthogonalisation energy...')
        if self.orthogonalisation_energy is not None:
            return self.orthogonalisation_energy
        else:
            self.compute_chemisorption_energy()
            return float(self.orthogonalisation_energy)
        
    def compute_chemisorption_energy(self):
        """Compute the chemisorption energy based on the 
        parameters of the class, a linear repulsion term
        and the hybridisation energy coming from the 
        Newns-Anderson model."""

        self.get_hybridisation_energy()
        self.get_occupancy()
        self.get_dband_filling()

        # orthonogonalisation energy
        self.orthogonalisation_energy = 2 * ( self.occupancy.real +  self.filling.real ) * self.alpha * self.Vak**2
        assert self.orthogonalisation_energy >= 0

        # chemisorption energy is the sum of the hybridisation
        # and the orthogonalisation energy
        self.chemisorption_energy = self.hybridisation_energy + self.orthogonalisation_energy 
        # Add the constant offset which is helpful for fitting routines
        self.chemisorption_energy += self.constant_offset