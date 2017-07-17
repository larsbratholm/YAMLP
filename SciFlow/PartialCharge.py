import numpy as np
import ImportData
import CoulombMatrix
from scipy.special import factorial

class PartialCharges():

    def __init__(self, matrixX, matrixY, matrixQ):
        """
        :param matrixX: a list of lists of atom labels and coordinates. size (n_samples, n_atoms*4)
        :param matrixY: a numpy array of energy values of size (N_samples,)
        :param matrixQ: a list of numpy arrays containing the partial charges of each atom. size (n_samples, n_atoms)
        """
        self.rawX = matrixX
        self.rawQ = matrixQ
        self.rawY = matrixY

        self.Z = {
            'C': 6.0,
            'H': 1.0,
            'N': 7.0
        }

        self.ene_pbe = {
            'H': 0.46437552,
            'C': 37.19463954,
            'N': 53.68235533
        }

        self.ene_ccsd = {
            'H': 0.49984482,
            'C': 37.72993039,
            'N': 54.41916828
        }

        self.n_atoms = int(len(self.rawX[0])/4)
        self.n_samples = len(self.rawX)

        self.diag_hyb_1 = np.zeros(self.n_atoms)
        self.diag_hyb_2 = np.zeros(self.n_atoms)

        self.partQCM = np.zeros((self.n_samples, int(self.n_atoms * (self.n_atoms+1) * 0.5)))
        self.partQCM24 = np.zeros((self.n_samples, int(self.n_atoms * (self.n_atoms+1) * 0.5)))
        self.diagQ = np.zeros((self.n_samples, self.n_atoms))

    def __generate_pccm(self):
        """
        This function makes the (n_samples, n_atoms^2) partial charge coulomb matrix where the diagonal elements are
        the qi^2. It also calculates the diagonal elements for the hybrid partial charge matrix.
        :return: (n_samples, n_atoms^2) numpy array
        """
        pccm = np.zeros((self.n_samples, int(self.n_atoms * self.n_atoms)))

        # This is a coulomb matrix for one particular sample in the dataset
        indivPCCM = np.zeros((self.n_atoms, self.n_atoms))
        sampleCount = 0

        for i in range(self.n_samples):
            # Making a vector with the coordinates of the atoms in this data sample
            coord = []
            labels = ""  # This is a string containing all the atom labels
            currentSamp = self.rawX[i]

            for j in range(0, len(currentSamp), 4):
                labels += currentSamp[j]
                coord.append(np.asarray([currentSamp[j + 1], currentSamp[j + 2], currentSamp[j + 3]]))

            # Calculating the diagonal elements for the hybrid 1 and 2 partial charge coulomb matrix
            for j in range(self.n_atoms):
                self.diag_hyb_1[j] = 0.5 * self.Z[labels[j]] ** 2.4
                self.diag_hyb_2[j] = self.ene_pbe[labels[j]]

            # Populating the diagonal elements
            for j in range(self.n_atoms):
                indivPCCM[j, j] = self.rawQ[i][j] ** 2

            # Populating the off-diagonal elements
            for j in range(self.n_atoms - 1):
                for k in range(j + 1, self.n_atoms):
                    # Distance between two atoms
                    distanceVec = coord[j] - coord[k]
                    distance = np.sqrt(np.dot(distanceVec, distanceVec))
                    # Putting the partial charge in
                    indivPCCM[j, k] = self.rawQ[i][j] * self.rawQ[i][k] / distance
                    indivPCCM[k, j] = indivPCCM[j, k]

            # The partial charge CM for each sample is flattened and added to the total matrix
            pccm[sampleCount, :] = indivPCCM.flatten()
            sampleCount += 1

        return pccm

    def get_pccm(self):
        """
        This function returns the partial charge coulomb matrix generated by __generate_pccm()
        :return: partial charge coulomb matrix numpy array (n_samples, n_atoms^2)
        """
        return self.pccm

    def generatePCCM(self, numRep=1):
        """
        This function generates the new CM that has partial charges instead of the nuclear charges. The diagonal elements
        are q_i^2 while the off diagonal elements are q_i*q_j / R_ij. The descriptor is randomised in the same way as
        the randomly sorted coulomb matrix and becomes an array of size (n_samples*numRep, n_atoms^2)
        :numRep: number of randomly sorted matrices to generate per sample data - int
        :return: numpy array of size (n_samples*numRep, n_atoms*(n_atoms+1)*0.5),
        y: extended matrix of energies, numpy array of size (n_samples*numRep,)
        """

        pccm = self.__generate_pccm()

        #  This randomises the coulomb matrix and trims away the duplicate values in the matrix since it is a diagonal matrix
        self.partQCM, self.y = self.__randomSort(pccm, self.rawY, numRep)

        print "Generated the partial charge coulomb matrix."

        return self.partQCM, self.y

    def __randomSort(self, X, y, numRep):
        """
        This function randomly sorts the rows and columns of the coulomb matrices depending on their column norm. It generates a
        matrix of size (n_samples*numRep, n_atoms^2)
        :numRep: The number of randomly sorted matrices to be generated for each data sample.
        :return: ranSort: numpy array of size (n_samples*numRep, n_atoms*(n_atoms+1)/2),
                y_bigdata: a numpy array of energy values of size (N_samples*numRep,)
        """

        # Checking reasonable numRep value
        if (isinstance(numRep, int) == False):
            print "Error: you gave a non-integer value for the number of RSCM that you want to generate."
            return None
        elif (numRep < 1):
            print "Error: you cannot generate less than 1 RSCM per sample. Enter an integer value > 1."

        counter = 0
        ranSort = np.zeros((self.n_samples * numRep, int(self.n_atoms * (self.n_atoms+1) * 0.5)))
        y_bigdata = np.zeros((self.n_samples * numRep,))

        for i in range(self.n_samples):
            tempMat = np.reshape(X[i, :], (self.n_atoms, self.n_atoms))

            # Calculating the norm vector for the coulomb matrix
            rowNorms = np.zeros(self.n_atoms)

            for j in range(self.n_atoms):
                rowNorms[j] = np.linalg.norm(tempMat[j, :])

            for k in range(numRep):
                # Generating random vectors and adding to the norm vector
                randVec = np.random.normal(loc=0.0, scale=np.std(rowNorms), size=self.n_atoms)
                rowNormRan = rowNorms + randVec
                # Sorting the new random norm vector
                permutations = np.argsort(rowNormRan)
                permutations = permutations[::-1]
                # Sorting accordingly the Coulomb matrix
                tempRandCM = tempMat[permutations, :]
                tempRandCM = tempRandCM[:,permutations]
                # Adding flattened randomly sorted Coulomb matrix to the final descriptor matrix
                ranSort[counter, :] = self.__trimAndFlat(tempRandCM)
                counter = counter + 1

            # Copying multiple values of the energies
            y_bigdata[numRep * i:numRep * i + numRep] = y[i]

        return ranSort, y_bigdata

    def __trimAndFlat(self, X):
        """
        This function takes a coulomb matrix and trims it so that only the upper triangular part of the matrix is kept.
        It returns the flattened trimmed array.
        :param X: Coulomb matrix for one sample. numpy array of shape (n_atoms, n_atoms)
        :return: numpy array of shape (n_atoms*(n_atoms+1)/2, )
        """
        size = int(self.n_atoms * (self.n_atoms+1) * 0.5)
        temp = np.zeros((size,))
        counter = 0

        for i in range(self.n_atoms):
            for j in range(i, self.n_atoms):
                temp[counter] = X[i][j]
                counter = counter + 1

        return temp

    def __partial_randomisation(self, X, y_data, numRep):
        """
        This function generates a coulomb matrix with randomisation but where only the coloumns of elements that are the
        same are swapped around.
        :param X: the (n_samples, n_atoms^2) coulomb matrix to randomise and trim
        :param y_data: the y_data in a (n_samples,) shape
        :param numRep: The largest number of swaps to do
        :return: the new Coulomb matrix (n_samples*n, n_features) and the y array in shape (n_samples*min(n_perm, numRep),)
        """
        PRCM = []

        for j in range(self.n_samples):
            flatMat = X[j]
            currentMat = np.reshape(flatMat, (self.n_atoms, self.n_atoms))

            # Check if there are two elements that are the same (check elements along diagonal)
            diag = currentMat.diagonal()
            idx_sort = np.argsort(diag)
            sorted_diag = diag[idx_sort]
            vals, idx_start, count = np.unique(sorted_diag, return_counts=True, return_index=True)

            # Work out the number of possible permutations n_perm
            permarr = factorial(count)
            n_perm = int(np.prod(permarr))

            # Decide which one is smaller, numRep or n_perm
            if numRep >= n_perm:
                isNumRepBigger = True
            else:
                isNumRepBigger = False

            # Finding out which rows/columns need permuting. Each element of dupl_col is a list of the indexes of the
            # columns that can be permuted.
            dupl_col = []
            for j in range(count.shape[0]):
                dupl_ind = range(idx_start[j],idx_start[j]+count[j])
                dupl_col.append(dupl_ind)

            # Permute the appropriate indexes randmoly
            if isNumRepBigger:
                permut_idx = self.permutations(dupl_col, n_perm, self.n_atoms)
            else:
                permut_idx = self.permutations(dupl_col, numRep, self.n_atoms)

            # Order the rows/coloumns in terms of smallest to largest diagonal element
            currentMat = currentMat[idx_sort, :]
            currentMat = currentMat[:, idx_sort]

            # Apply the permutations that have been obtained to the rows and columns
            for i in range(min(numRep,n_perm)):
                currentMat = currentMat[permut_idx[i], :]
                currentMat = currentMat[:, permut_idx[i]]
                PRCM.append(self.__trimAndFlat(currentMat))

        # Turn PRCM into a numpy array of size (n_samples*min(n_perm, numRep), n_features)
        PRCM = np.asarray(PRCM)

        # Modify the shape of y
        y_big = np.asarray(np.repeat(y_data,min(n_perm, numRep)))

        return PRCM, y_big

    def permutations(self, col_idx, num_perm, n_atoms):
        """
        This function takes a list of the columns that need permuting. It returns num_perm arrays of permuted indexes.
        :param col_idx: list of list of columns that need swapping around
        :param num_perm: number of permutations desired (int)
        :param n_atoms: total number of atoms in the system
        :return: an array of shape (num_perm, n_atoms) of permuted indexes.
        """
        all_perm = np.zeros((num_perm, n_atoms), dtype=np.int8)
        temp = col_idx

        for j in range(num_perm):
            for i in range(len(col_idx)):
                temp[i] = np.random.permutation(col_idx[i])
            flat_temp = [item for sublist in temp for item in sublist]
            all_perm[j, :] = flat_temp

        return all_perm

    def hybrid_pccm_1(self, numRep=5):
        """
        The off-diagonal elements are qiqj/rij the diagonal elements are the 0.5*Z^2.4
        :param numReps: number of randomisations to do per sample
        :return: (n_samples*n, n_features) numpy array with partial charge coulomb matrix. Y_big: numpy array of size
        (n_samples*min(n_perm, numRep).
        """
        pccm = self.__generate_pccm()

        # Modifying the diagonal elements to be the nuclear charge ones
        for i in range(pccm.shape[0]):
            for j in range(self.n_atoms):
                pccm[i][self.n_atoms*j+j] = self.diag_hyb_1[j]

        # Doing partial randomisation and trimming
        trim_rand_pccm, y_big = self.__partial_randomisation(pccm, self.rawY, numRep)

        return trim_rand_pccm, y_big

    def hybrid_pccm_2(self, numRep=5):
        """
        The off-diagonal elements are qiqj/rij the diagonal elements are the calculated PBE energies of the free atoms.
        :param numReps: number of randomisations to do per sample
        :return: (n_samples*n, n_features) numpy array with partial charge coulomb matrix. Y_big: numpy array of size
        (n_samples*min(n_perm, numRep).
        """
        pccm = self.__generate_pccm()

        # Modifying the diagonal elements to be the nuclear charge ones
        for i in range(pccm.shape[0]):
            for j in range(self.n_atoms):
                pccm[i][7 * j + j] = self.diag_hyb_2[j]

        # Doing partial randomisation and trimming
        trim_rand_pccm, y_big = self.__partial_randomisation(pccm, self.rawY, numRep)

        return trim_rand_pccm, y_big



if __name__ == "__main__":
    def testMatrix():
        X = [["H", 0.0, 0.0, 0.0, "H", 1.0, 0.0, 0.0, "C", 0.5, 0.5, 0.5, "C", 0.5, 0.7, 0.5, "N", 0.5, 0.5, 0.8 ],
             ["H", 0.1, 0.0, 0.0, "H", 0.9, 0.0, 0.0, "C", -0.5, -0.5, -0.5, "C", 0.1, 0.5, 0.5, "N", 0.6, 0.5, 0.5,],
                ["H", -0.1, 0.0, 0.0, "H", 1.1, 0.0, 0.0, "C", 1.0, 1.0, 1.0, "C", 0.3, 0.5, 0.3, "N", 1.5, 2.5, 0.5,]]
        y = np.array([4.0, 3.0, 1.0])
        Q = np.array([[1.0, 1.0, 6.0, 6.0, 7.0], [1.0, 1.0, 6.0, 6.0, 7.0], [1.0, 1.0, 6.0, 6.0, 7.0]])
        return X, y, Q

    X, y, Q = testMatrix()
    CM = PartialCharges(X, y, Q)
    CM.hybrid_pccm_1()

    # X, y, q = ImportData.loadPd_q("/Users/walfits/Repositories/trainingdata/per-user-trajectories/CH4+CN/pruning/dataSets/pbe_b3lyp_partQ.csv")
    # mat = PartialCharges(X, y, q)
