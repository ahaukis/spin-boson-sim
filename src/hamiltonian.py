from qutip import *
from src.conversions import *
from math import ceil
from copy import deepcopy
from qiskit.quantum_info import Operator, SparsePauliOp, Statevector
import itertools
import numpy as np


def jaynes_cummings_ham(Delta: int = 0, g: int = 1, cutoff = 2):

    h_tls = ([sigmaz(), identity(cutoff)], 0.5 * Delta)
    h_int1 = ([sigmap(), destroy(cutoff)], g)
    h_int2 = ([sigmam(), create(cutoff)], g)

    photon_ind = [1]

    H_list = [h_tls, h_int1, h_int2]

    return HamiltonianList(H_list, photon_ind, cutoff)


### HamiltonianList class ###

class HamiltonianList:

    def __init__(self, H_list: list, photon_indices: list[int], cutoff: int):
        """H_list must be a list of all terms in the Hamiltonian,
        where each term is a list of tuples,
        where the 1st element of the tuple is a list of tensor product factors
        and the 2nd element is the coefficient of the term."""
        self._terms = H_list
        self._photon_ind = photon_indices
        self._cutoff = cutoff
    
    @property
    def terms(self):
        return self._terms
    
    @property
    def photon_ind(self):
        return self._photon_ind
    
    @property
    def cutoff(self):
        return self._cutoff
    
    def qubits_per_photon(self):
        return ceil(np.log2(self.cutoff))
    
    def num_terms(self):
        """Returns the number of terms in the Hamiltonian."""
        return len(self.terms)
    
    def num_dof(self):
        """Returns the number of degrees of freedom (factors in each term.)"""
        return len(self.terms[0][0])
    
    def num_photons(self):
        """Returns the number of photonic degrees of freedom in the system."""
        return len(self.photon_ind)
    
    def full_hamiltonian(self) -> Qobj:
        """Returns the full Hamiltonian based on the list."""
        ham = Qobj()
        for i in range(self.num_terms()):
            factors = self.terms[i][0]
            coeff = self.terms[i][1]
            ham += coeff * tensor(factors)
        return ham
        
    def map_to_qubits(self, encoding: str = 'standard') -> SparsePauliOp:
        """
        Map Hamiltonian onto qubits. Qubit order such that first op. in the factors list
        is mapped to the first qubits according to qiskits qubit ordering.
        Args:
            encoding (str): Encoding for bosonic operators. 'standard' or 'graycode'.
        Returns:
            SparsePauliOp
        """

        for i, term in enumerate(self.terms):
            coeff = term[1]
            factors = term[0]
            for j, fact in enumerate(factors):
                if j in self.photon_ind:
                    op_q = qobj_to_sparsepauliop(fact, self.qubits_per_photon(), encoding=encoding)
                else:
                    # dummy conversion, ok for Pauli operators at least
                    op_q = SparsePauliOp.from_operator(Operator(fact.data.toarray()))
                if j == 0:
                    id_str = ''.join(['I' for _ in range(op_q.num_qubits)])
                    term_q = op_q.compose(SparsePauliOp(id_str, coeff))
                else:
                    term_q = term_q.expand(op_q)    # i.e. term_q = op_q (x) term_q
            if i == 0:
                hamiltonian_q = term_q
            else:
                hamiltonian_q = SparsePauliOp.sum([hamiltonian_q, term_q])
            
        return hamiltonian_q.simplify()
    