from .openTEPES_PowerData import *

def parse_matrix(matrix_lines):
    cleanLines = []
    for line in matrix_lines:
        cleanLines.append(line.split('%')[0].strip())
    matrix_string = ''.join(cleanLines)
    matrix_name = matrix_string.split('=')[0].strip();
    matrix_body = matrix_string.split('=')[1].strip();
    matrix_body = matrix_body.strip(';').strip('[').strip(']');
    matrix_rows = matrix_body.split(';')
    maxtrix = []
    columns = None
    for row in matrix_rows:
        row = row.strip();
        if len(row) > 0:
            maxtrix.append([item.strip() for item in row.split('\t')])
            if columns == None:
                columns = len(maxtrix[-1])
            else:
                if columns != len(maxtrix[-1]):
                    raise PFMError('matrix parsing error, inconsistent number of items in each row\n'+row)
    
    return {'name':matrix_name, 'data':maxtrix}

def extract_assignment(str):
    statement = str.split(';')[0]
    value = statement.split('=')[-1].strip()
    return value


def parse_mp_case(mpFileName):
    mpFile = open(mpFileName, 'r')
    
    firstLine = mpFile.readline();
    firstLineParts = firstLine.split(' ');
    name = firstLineParts[-1].strip();
    
    lines =  mpFile.readlines();
    tmp = []
    for line in lines:
        line = line.strip()
        if len(line) > 0 and line[0] != '%':
            tmp.append(line)
    lines = tmp       
    
    tmp = []
    for line in lines:
        #print line
        if 'function mpc =' in line:
            name = line.split('=')[1].strip()
        if 'mpc.version' in line:
            version = extract_assignment(line)
        elif 'mpc.baseMVA' in line:
            baseMVA = float(extract_assignment(line))
        else:
            tmp.append(line)
    lines = tmp  
    #print version, baseMVA
    #print(lines)
    
    if version != '\'2\'':
        raise PFMError('This parser only supports version 2. Given version '+version)
        
    matrixes = []
    matrix = []
    
    reading = False
    for line in lines:
        if '[' in line:
            reading = True;
        if reading:
            matrix.append(line);
        if ']' in line:
            reading = False;
            matrixes.append(matrix);
            matrix = []
    #print matrixes
    
    parsed_matrixes = []
    for matrix in matrixes:
        parsed_matrixes.append(parse_matrix(matrix));
    
    bus=None
    gen=None
    branch=None
    gencost=None
    
    for parsed_matrix in parsed_matrixes:
        if parsed_matrix['name'] == 'mpc.bus':
            bus = [Bus(*data) for data in parsed_matrix['data']]
        elif parsed_matrix['name'] == 'mpc.gen':
            gen = [Generator(i, *data) for i, data in enumerate(parsed_matrix['data'])]
        elif parsed_matrix['name'] == 'mpc.branch':
            branch = [Branch(i, *data) for i, data in enumerate(parsed_matrix['data'])]
        elif parsed_matrix['name'] == 'mpc.gencost':
            gencost = []
            for i, data in enumerate(parsed_matrix['data']):
                if int(data[0]) != 2:
                    raise PFMError('only generator cost model type 2 is supported. Given: '+str(data[0]));
                if int(data[3]) != 3:
                    raise PFMError('only qudratic generator cost model is supported. Given:'+str(data[3]));
                gencost.append(GeneratorCost(i, *data))
        else :
            print('Warning: Unrecognized data matrix named:', parsed_matrix['name'])
            print('         data was ignored')
    
    case = Case(name, baseMVA, bus, gen, branch, gencost)
    case = case.remove_status_zero()
    case.check();
    
    return case
    
    
    
    
    
    
    
    
    
    
    
    

