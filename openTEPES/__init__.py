"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES)


    Args:
        case:   Name of the folder where the CSV files of the case are found
        dir:    Main path where the case folder can be found
        solver: Name of the solver

    Returns:
        Output results in CSV files that are found in the case folder.

    Examples:
        >>> import openTEPES as oT
        >>> oT.routine("9n", "C:\\Users\\UserName\\Documents\\GitHub\\openTEPES", "glpk")
"""
__version__ = "4.18.17RC"

from .openTEPES_Main              import main
from .openTEPES                   import *
from .openTEPES_InputSchema       import *
from .openTEPES_InputSource       import *
from .openTEPES_InputCSVSource    import *
from .openTEPES_InputDuckDBSource import *
from .openTEPES_InputData         import *
from .openTEPES_ModelFormulation  import *
from .openTEPES_ProblemSolving        import *
from .openTEPES_ProblemSolvingBenders import *
from .openTEPES_OutputResultsCommon         import *
from .openTEPES_OutputResultsRawDump        import *
from .openTEPES_OutputResultsInvestment     import *
from .openTEPES_OutputResultsGeneration     import *
from .openTEPES_OutputResultsStorage        import *
from .openTEPES_OutputResultsHydrogen       import *
from .openTEPES_OutputResultsHeat           import *
from .openTEPES_OutputResultsNetwork        import *
from .openTEPES_OutputResultsEconomic       import *
from .openTEPES_OutputResultsSummary        import *
