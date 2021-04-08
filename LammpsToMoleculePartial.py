##############################################################################
# Developed by: Matthew Bone
# Last Updated: 08/04/2021
# Updated by: Matthew Bone
#
# Contact Details:
# Bristol Composites Institute (BCI)
# Department of Aerospace Engineering - University of Bristol
# Queen's Building - University Walk
# Bristol, BS8 1TR
# U.K.
# Email - matthew.bone@bristol.ac.uk
#
# File Description:
# Converts LAMMPS 'read_data' input files into LAMMPS molecule format files.
# Designed to work with LAMMPS data generated from Moltemplate, but can work
# for any LAMMPS data if it satisfies the header format in Assumptions.

# Assumptions:
# LAMMPS Atom Type is full
# That the header of the file operates in the standard format:
# Comment
#
#      a  atoms
#      b  bonds
#      c  angles
#      d  dihedrals
#      e  impropers

#      f  atom types
#      g bond types
#      h  angle types
#      i  dihedral types
#      j  improper types

#   x1 x2 xlo xhi
#   y1 y2 ylo yhi
#   z1 z2 zlo zhi
##############################################################################

import os
from natsort import natsorted
from LammpsTreatmentFuncs import clean_data, add_section_keyword, save_text_file, refine_data, format_comment, edge_atom_fingerprint_strings
from LammpsSearchFuncs import get_data, find_partial_structure, find_sections
from MappingFunctions import element_atomID_dict

def lammps_to_molecule_partial(directory, fileName, saveName, bondingAtoms: list):
    # Check that bonding atoms have been specified
    assert len(bondingAtoms) > 0, 'No bonding atoms have been specified'

    # Go to file directory
    os.chdir(directory)

    # Load file into python as a list of lists
    with open(fileName, 'r') as f:
        lines = f.readlines()
    
    # Tidy input
    tidiedLines = clean_data(lines)
    
    # Build sectionIndexList
    sectionIndexList = find_sections(tidiedLines)

    # Get original bonds data
    originalBonds = get_data('Bonds', tidiedLines, sectionIndexList)
    
    validAtomSet, edgeAtomList, edgeAtomFingerprintDict = find_partial_structure(bondingAtoms, originalBonds)

    # Get atoms data
    atoms = get_data('Atoms', tidiedLines, sectionIndexList)
    atoms, renumberedAtomIDDict = refine_data(atoms, 0, validAtomSet)

    # Get new bonds data
    bonds = refine_data(originalBonds, [2, 3], validAtomSet, renumberedAtomIDDict)
    bonds = add_section_keyword('Bonds', bonds)
    
    # Get angles data
    angles = get_data('Angles', tidiedLines, sectionIndexList)
    angles = refine_data(angles, [2, 3, 4], validAtomSet, renumberedAtomIDDict)
    angles = add_section_keyword('Angles', angles)

    # Get dihedrals
    dihedrals = get_data('Dihedrals', tidiedLines, sectionIndexList)
    dihedrals = refine_data(dihedrals, [2, 3, 4, 5], validAtomSet, renumberedAtomIDDict)
    dihedrals = add_section_keyword('Dihedrals', dihedrals)

    # Get impropers
    impropers = get_data('Impropers', tidiedLines, sectionIndexList)
    impropers = refine_data(impropers, [2, 3, 4, 5], validAtomSet, renumberedAtomIDDict)
    impropers = add_section_keyword('Impropers', impropers)

    # Rearrange atom data to get types, charges, coords - assume atom type full very important
    types = [[atom[0], atom[2]] for atom in atoms]
    types = add_section_keyword('Types', types)

    charges = [[atom[0], atom[3]] for atom in atoms]
    charges = add_section_keyword('Charges', charges)

    coords = [[atom[0], atom[4], atom[5], atom[6]] for atom in atoms]
    coords = add_section_keyword('Coords', coords)

    # Get and change header values
    header = tidiedLines[1:6]
    header = [val.split() for val in header]
    # Update numbers with new lengths of data
    for index, data in enumerate([types, bonds, angles, dihedrals, impropers]):
        if len(data) > 0: # This corrects for the added section keyword lines
            header[index][0] = str(len(data) - 3)
        else:
            header[index][0] = str(0)
    header.insert(0, ['\n'])

    # Format edge atom fingerprints
    elementAtomIDDict = element_atomID_dict(directory, fileName, ['H', 'H', 'C', 'C', 'N', 'O', 'O', 'O'])
    
    edgeElementFingerprintDict = edge_atom_fingerprint_strings(edgeAtomFingerprintDict, elementAtomIDDict)

    # Convert dictionary to list of lists, renumber edge atoms, and reduce to a list
    edgeElementFingerprintList = [[key, atomString] for key, atomString in edgeElementFingerprintDict.items()]
    renumberedEdgeFingerprints = [[renumberedAtomIDDict[fingerprint[0]], fingerprint[1]] for fingerprint in edgeElementFingerprintList]
    renumberedEdgeFingerprints = [value for fingerprintList in edgeElementFingerprintList for value in fingerprintList]

    # Renumber bonding and edge atom comments with new atomIDs
    renumberedBondingAtoms = [renumberedAtomIDDict[ba] for ba in bondingAtoms]
    renumberedEdgeAtoms = [renumberedAtomIDDict[ea] for ea in edgeAtomList]
    
    # Add bond and edge atoms as comment in header
    bondAtoms = format_comment(renumberedBondingAtoms, '# Bonding_Atoms ')
    edgeAtoms = format_comment(renumberedEdgeAtoms, '# Edge_Atoms ')
    edgeFingerprints = format_comment(renumberedEdgeFingerprints, '# Edge_Atom_Fingerprints ')
    commentString = [bondAtoms, edgeAtoms, edgeFingerprints]

    # Combine to one long output list
    outputList = []
    totalList = [commentString, header, types, charges, coords, bonds, angles, dihedrals, impropers]
    
    for keyword in totalList:
        outputList.extend(keyword)
        
    # Output as text file
    save_text_file(saveName + 'molecule.data', outputList)
