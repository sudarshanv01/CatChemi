"""Account for linear repulsive term from overlap."""

import numpy as np
from catchemi import NewnsAndersonNumerical

class NewnsAndersonLinearRepulsion(NewnsAndersonNumerical):
    """Class that provides the Newns-Anderson hybridisation
    energy along with the linear orthogonalisation energy.
    It subclasses NewnsAndersonNumerical for the Hybridisation
    energy and adds the orthogonalisation penalty separately."""

    def __init__(self, Vsd, eps_a, eps_d, width, eps, 
                 Delta0_mag=0.0, eps_sp_max=15, eps_sp_min=-15,
                 precision=50, verbose=False,
                 alpha=0.0, beta=0.0, constant_offset=0.0, spin=2):
        Vak = np.sqrt(beta) * Vsd
        super().__init__(Vak, eps_a, eps_d, width, 
                         eps, Delta0_mag, eps_sp_max,
                         eps_sp_min, precision, verbose, spin)
        self.alpha = alpha
        self.beta = beta
        assert self.alpha >= 0.0, "alpha must be positive."
        assert self.beta >= 0.0, "beta must be positive."
        self.constant_offset = constant_offset

        # The goal is to find the chemisorption energy
        self.chemisorption_energy = None
        # Also store the orthogonalisation energy
        self.orthogonalisation_energy = None
        # Store the spin
        self.spin = spin
    
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
        self.orthogonalisation_energy = self.spin * ( self.occupancy.real +  self.filling.real ) * self.alpha * self.Vak**2
        assert self.orthogonalisation_energy >= 0

        # chemisorption energy is the sum of the hybridisation
        # and the orthogonalisation energy
        self.chemisorption_energy = self.hybridisation_energy + self.orthogonalisation_energy 
        # Add the constant offset which is helpful for fitting routines
        self.chemisorption_energy += self.constant_offset