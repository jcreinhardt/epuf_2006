#income stream modifer, this has not changed since 1967, look on page 14 of 1967 pdf

import numpy as np
from leg_1939 import *
from leg_1943 import *
from leg_1944 import *
from leg_1945 import *
from leg_1946 import *
from leg_1947 import *
from leg_1950 import *
from leg_1952 import *
from leg_1954 import *
from leg_1956 import *
from leg_1958 import *
from leg_1960 import *
from leg_1961 import *
from leg_1965 import *
from leg_1966 import *
from leg_1967 import *


def i1969(income_stream:list, index_year:int, retirement_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1967 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy()
    for i in range(len(income_stream)):
        if income_stream[i]>3000 and (index_year+i)<1951:
            adjusted_income_stream[i]=3000
        if income_stream[i]>3600 and (index_year+i)<1955 and (index_year+i)>1950:
            adjusted_income_stream[i]=3600
        if income_stream[i]>4200 and (index_year+i)>=1955 and (index_year+i)<=1958:
            adjusted_income_stream[i]=4200
        if income_stream[i]>4800 and (index_year+i)<=1965 and (index_year+i)>=1959:
            adjusted_income_stream[i]=4800      
        if income_stream[i]>6600 and (index_year+i)<=1967 and (index_year+i)>=1966:
            adjusted_income_stream[i]=6600 
        if income_stream[i]>7800 and (index_year+i)>=1968:
            adjusted_income_stream[i]=7800 
    return adjusted_income_stream

# @Daniel I don't think this changed since 1960 please double check me! I don't think it has either!

def a1969(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, death_year = 0):
    """This function returns the average monthly wage (int) of an individual as determined by the 1952 legislation.
        This is more complicated than one might think, which is why it has its own seperate function.
        The inputs are (adjusted_income_stream:list,index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, adjusted by the relevant legislation. i1952 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream   
        birth_year -- the year the individual is born.
        woman -- gender of recipient, True if a woman
    """   
    #initializing
    total_wage=0
    avg_monthly_wage_A=0
    avg_monthly_wage_B=0

    # Create a copy of adjusted_income_stream
    adjusted_income_copy = adjusted_income_stream.copy()
    startIndex = max(0, 1951-index_year)
    index_year = max(1951, index_year)
    adjusted_income_stream = adjusted_income_stream[startIndex : ]
    

###################

    #Case 1: The starting date is 1950, we initially coded this wrong, post 1961 version, years after age 62 don't count for elapsed years purposes
    beginning_year=1951
    if death_year == 0:
        if woman==True:
            end_year=max(1961, birth_year+62) #note that this is different from the previus legislation, "first entitled" now means age 62 in the legislation
        else:
            end_year=max(1961, birth_year+65)
    else:
        if woman==True:
            end_year=max(1961, min(death_year, birth_year+62)) #note that this is different from the previus legislation, "first entitled" now means age 62 in the legislation
        else:
            end_year=max(1961, min(death_year,birth_year+65))

    drops = 5
    elasped_years=end_year-beginning_year
    
    highest_years=elasped_years-drops
    
    if highest_years<2:
        highest_years=2
    
    highest_indices = np.argsort(adjusted_income_stream)[-highest_years:] #python is right exclusive
    
    for i in range(len(adjusted_income_stream)): 
        if (i+index_year)>=beginning_year and (i in highest_indices):
            total_wage+=adjusted_income_stream[i]


    count = highest_years 
    yrBefore22andNotCovered = 0
    yr_22 = birth_year + 22


    #as of 4/29/25 This needs to be fixed, but I am fine with assuming everyone starts working at 22
    # if yr_22 > beginning_year: 
    #     for i in range(beginning_year,yr_22): # Go through all years they are < 22 age
    #         if (i-index_year) > 0 and adjusted_income_stream[i-index_year]<200: # Check that it is a valid income index and they make less than 200. Does this even work as planned? I need to fix this??????
    #             yrBefore22andNotCovered += 1 # Add one to not covered

    count = count - yrBefore22andNotCovered 
    avg_monthly_wage_A=total_wage/(max(24,count*12))

###################
    # Case 2: if you are born after 1951 you can use a different forum
    if birth_year+22>1950:#the reasoning here is that there is a distinction in the legislation between those who turn 22 before and after 1950.
        #Those who turn 22 after 1950 have the option to use either their age 22 income onward or 1950 income onwards to calculate the average montly wage, the method that maximizes average monthly wage is used automatically
        #Case 2: The starting date is year they turn 22
        beginning_year=1951
        if woman==True:
            end_year=max(1961,birth_year+62) #note that this is different from the previus legislation, "first entitled" now means age 62 in the legislation
        else:
            end_year=max(1961, birth_year+65)
        drops=5
    
        elasped_years=end_year-beginning_year-1
        highest_years=elasped_years-drops
        if highest_years<2:
        	highest_years=2
        
        highest_indices= np.argsort(adjusted_income_stream)[-highest_years:]  
        
        for i in range(len(adjusted_income_stream)): 
            if (i+index_year)>=beginning_year and (i in highest_indices):
                total_wage+=adjusted_income_stream[i]
        
        count = highest_years 
        yrBefore22andNotCovered = 0
        yr_22 = birth_year + 22
    
    
        #as of 4/29/25 This needs to be fixed, but I am fine with assuming everyone starts working at 22
        # if yr_22 > beginning_year: 
        #     for i in range(beginning_year,yr_22): # Go through all years they are < 22 age
        #         if (i-index_year) > 0 and adjusted_income_stream[i-index_year]<200: # Check that it is a valid income index and they make less than 200. Does this even work as planned? I need to fix this??????
        #             yrBefore22andNotCovered += 1 # Add one to not covered
    
        count = count - yrBefore22andNotCovered 
        avg_monthly_wage_B=total_wage/(max(24,count*12))
        
###################

    avg_monthly_wage=max(avg_monthly_wage_A, avg_monthly_wage_B)
    # print(avg_monthly_wage)
    return avg_monthly_wage
    

#see 1961 pdf page 7, was not update in 1967
def q1969(adjusted_income_stream:list,original_income_stream:list,  index_year:int, birth_year:int,  retirement_year:int, woman:bool, skip1939 = False): #this might not be completely correct/ might be off by half a year
    """This function determines whether an individual is considered fully-insured as of the 1950 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1950 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
        woman -- gender of recipient, True if a woman
    """
    
    if skip1939 == False and q1939(i1939(original_income_stream, index_year, retirement_year), index_year, birth_year, retirement_year, woman): return True
    if (retirement_year < birth_year+62): return False
    startIndex = max(0, 1950-index_year)
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    for i in range(startIndex, len(adjusted_income_stream)):
        if adjusted_income_stream[i]>= 50 and adjusted_income_stream[i] < 100:
            coverage_quarters+=1
        elif adjusted_income_stream[i] >= 100 and adjusted_income_stream[i] < 150:
            coverage_quarters+= 2
        elif adjusted_income_stream[i] >= 150 and adjusted_income_stream[i] < 200:
            coverage_quarters+= 3
        elif adjusted_income_stream[i] >= 200:
            coverage_quarters+= 4

    if woman: end_year = birth_year +62
    else: end_year = birth_year+65
    reference_year=max(1951,birth_year+21) #odd nuance of the legislation
    # print(coverage_quarters)
    # print(end_year, reference_year, end_year - reference_year)
    if coverage_quarters>40:
        return True
    elif ((coverage_quarters)>=((4/4)*(end_year)-reference_year)) and (coverage_quarters>=6):
        return True
    else:
        return False

def qcurrent1969(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
    """This function determines whether an individual is considered fully-insured as of the 1939 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int)
        income_stream -- a list of nominal incomes a person received in each year
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """

    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    if len(income_stream) < 3 or death_year >= reference_year : return False
    for income in income_stream[-3:]:
        if income>=200:
            coverage_quarters+=4
        elif income >=150:
            coverage_quarters +=3
        elif income >=100:
            coverage_quarters +=2
        elif income >=100:
            coverage_quarters +=1
    
    if coverage_quarters >= 6: return True
    else: return False


#benefit rules pdf page 251 of 1969 pdf
def bb1969(adjusted_income_stream:list, original_income_stream:list,  avg_monthly_wage:int, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    pia=0
    pib=0 
    pia_1967=0
    
    #avg_monthly_wage=a1969(adjusted_income_stream, index_year, birth_year,retirement_year, woman)

    pib = b1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    pia_1967 = b1967(i1967(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year,  reference_year, woman) 
    

    pib_list = [
        [0, 16.20], [16.21, 16.84], [16.85, 17.60], [17.61, 18.40],
        [18.41, 19.24], [19.25, 20.00], [20.01, 20.64], [20.65, 21.28],
        [21.29, 21.88], [21.89, 22.28], [22.29, 22.68], [22.69, 23.08],
        [23.09, 23.44], [23.45, 23.76], [23.77, 24.20], [24.21, 24.60],
        [24.61, 25.00], [25.01, 25.48], [25.49, 25.92], [25.93, 26.40],
        [26.41, 26.94], [26.95, 27.46], [27.47, 28.00], [28.01, 28.68],
        [28.69, 29.25], [29.26, 29.68], [29.69, 30.36], [30.37, 30.92],
        [30.93, 31.36], [31.37, 32.00], [32.01, 32.60], [32.61, 33.20],
        [33.21, 33.88], [33.89, 34.50], [34.51, 35.00], [35.01, 35.80],
        [35.81, 36.40], [36.41, 37.08], [37.09, 37.60], [37.61, 38.20],
        [38.21, 39.12], [39.13, 39.68], [39.69, 40.33], [40.34, 41.12],
        [41.13, 41.76], [41.77, 42.44], [42.45, 43.20], [43.21, 43.76],
        [43.77, 44.44], [44.45, 44.88], [44.89, 45.60]
    ]
    
    pia_1965_list = [ #this will need to be fixed!
        55.40, 56.50, 57.70, 58.80, 59.90, 61.10, 62.20, 63.30, 64.50, 65.60,
        66.70, 67.80, 69.00, 70.20, 71.50, 72.60, 73.80, 75.10, 76.30, 77.50,
        78.70, 79.90, 81.10, 82.30, 83.60, 84.70, 85.90, 87.20, 88.40, 89.50,
        90.80, 92.00, 93.20, 94.40, 95.60, 96.80, 98.00, 99.30, 100.50, 101.60,
        102.90, 104.10, 105.20, 106.50, 107.70, 108.90, 110.10, 111.40, 112.60, 113.70,
        115.00, 116.20, 117.30, 118.60, 119.80, 121.00, 122.20, 123.40, 124.70, 125.80,
        127.10, 128.30, 129.40, 130.70, 131.90, 133.00, 134.30, 135.50, 136.80, 137.90,
        139.10, 140.40, 141.50, 142.80, 144.00, 145.10, 146.40, 147.60, 148.90, 150.00,
        151.20, 152.50, 153.60, 154.90, 156.00, 157.10, 158.20, 159.40, 160.50, 161.60,
        162.80, 163.90, 165.00, 166.20, 167.30, 168.40, 169.50, 170.70, 171.80, 172.90,
        174.10, 175.20, 176.30, 177.50, 178.60, 179.70, 180.80, 182.00, 183.10, 184.20,
        185.40, 186.50, 187.60, 188.80, 189.90, 191.00, 192.00, 193.00, 194.00, 195.00,
        196.00, 197.00, 198.00, 199.00, 200.00, 201.00, 202.00, 203.00, 204.00, 205.00,
        206.00, 207.00, 208.00, 209.00, 210.00, 211.00, 212.00, 213.00, 214.00, 215.00,
        216.00, 217.00, 218.00
    ]
    
    avg_monthly_wage_list = [
        [0, 77], [77, 79], [79, 81], [81, 82], [82, 84], [84, 86], [86, 88], [88, 90], [90, 91], [91, 93],
        [93, 95], [95, 97], [97, 98], [98, 100], [100, 102], [102, 103], [103, 105], [105, 107], [107, 108], [108, 110],
        [110, 114], [114, 119], [119, 123], [123, 128], [128, 133], [133, 137], [137, 142], [142, 147], [147, 151], [151, 156],
        [156, 161], [161, 165], [165, 170], [170, 175], [175, 179], [179, 184], [184, 189], [189, 194], [194, 198], [198, 203],
        [203, 208], [208, 212], [212, 217], [217, 222], [222, 226], [226, 231], [231, 236], [236, 240], [240, 245], [245, 250],
        [250, 254], [254, 259], [259, 264], [264, 268], [268, 273], [273, 278], [278, 282], [282, 287], [287, 292], [292, 296],
        [296, 301], [301, 306], [306, 310], [310, 315], [315, 320], [320, 324], [324, 329], [329, 334], [334, 338], [338, 343],
        [343, 348], [348, 352], [352, 357], [357, 362], [362, 366], [366, 371], [371, 376], [376, 380], [380, 385], [385, 390],
        [390, 394], [394, 399], [399, 404], [404, 408], [408, 413], [413, 418], [418, 422], [422, 427], [427, 432], [432, 437],
        [437, 441], [441, 446], [446, 451], [451, 455], [455, 460], [460, 465], [465, 469], [469, 474], [474, 479], [479, 483],
        [483, 488], [488, 493], [493, 497], [497, 502], [502, 507], [507, 511], [511, 516], [516, 521], [521, 525], [525, 530],
        [530, 535], [535, 539], [539, 544], [544, 549], [549, 554], [554, 557], [557, 561], [561, 564], [564, 568], [568, 571],
        [571, 575], [575, 578], [578, 582], [582, 585], [585, 589], [589, 592], [592, 596], [596, 599], [599, 603], [603, 606],
        [606, 610], [610, 613], [613, 617], [617, 621], [621, 624], [624, 628], [628, 631], [631, 635], [635, 638], [638, 642],
        [642, 645], [645, 649], [649, 651]
    ]


    pia_list = [
        64.00, 65.00, 66.40, 67.70, 68.90, 70.30, 71.60, 72.80, 74.20, 75.50,
        76.80, 78.00, 79.40, 80.80, 82.30, 83.50, 84.90, 86.40, 87.80, 89.20,
        90.60, 91.90, 93.30, 94.70, 96.20, 97.50, 98.80, 100.30, 101.70, 103.00,
        104.50, 105.80, 107.20, 108.60, 110.00, 111.40, 112.70, 114.20, 115.60, 116.90,
        118.40, 119.80, 121.00, 122.50, 123.90, 125.30, 126.70, 128.20, 129.50, 130.80,
        132.30, 133.70, 134.90, 136.40, 137.80, 139.20, 140.60, 142.00, 143.50, 144.70,
        146.20, 147.60, 148.90, 150.40, 151.70, 153.00, 154.50, 155.90, 157.40, 158.60,
        160.00, 161.50, 162.80, 164.30, 165.60, 166.90, 168.40, 169.80, 171.30, 172.50,
        173.90, 175.40, 176.70, 178.20, 179.40, 180.70, 182.00, 183.40, 184.60, 185.90,
        187.30, 188.50, 189.80, 191.20, 192.40, 193.70, 195.00, 196.40, 197.60, 198.90,
        200.30, 201.50, 202.80, 204.20, 205.40, 206.70, 208.00, 209.30, 210.60, 211.90,
        213.30, 214.50, 215.80, 217.20, 218.40, 219.70, 220.80, 222.00, 223.10, 224.30,
        225.40, 226.60, 227.70, 228.90, 230.00, 231.20, 232.30, 233.50, 234.60, 235.80,
        236.90, 238.10, 239.20, 240.40, 241.50, 242.70, 243.80, 245.00, 246.10, 247.30,
        248.40, 249.60, 250.70
    ]

    pia_A=0
    pia_B=0
    pia_C=0

    #actual benefit formula
    if ((q1969(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year,woman, skip1939 = True)==True)): #Check if the worker is fully-insured, as well as to place them in the proper formula
        for i in range(len(avg_monthly_wage_list)):
            if avg_monthly_wage>=avg_monthly_wage_list[i][0] and avg_monthly_wage<avg_monthly_wage_list[i][1]:
                pia_A=pia_list[i]
    if ((q1969(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year,woman)==True) and (birth_year+65<1950)):
        for i in range(len(pib_list)):
            if pib>=pib_list[i][0] and pib<=pib_list[i][1]:
                pia_B=pia_list[i]
    if ((q1969(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year,woman, skip1939 = True)==True) and (birth_year+65<1969)):
        for i in range(len(pia_1965_list)):
            if pia_1967>=pia_1965_list[i] and pia_1967<pia_1965_list[i-1]:
                pia_C=pia_list[i]
    #legislation says to take the maximum of these   
    #print(pia_A, pia_B, pia_C)     
    pia=max(pia_A, pia_B, pia_C)


    # max_benefit=max(max_benefit_A,max_benefit_B,max_benefit_C)
    return pia #, max_benefit
              
              
def b1969(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        woman -- gender of recipient, True if a woman
    """ 
    #retirement_year=index_year+len(income_stream)
    monthly_benefits=0
    adjusted_income_stream=i1969(income_stream, index_year, retirement_year)
    if not q1969(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, woman): return 0

    if retirement_year <= 1950: avg_monthly_wage = a1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1952 : avg_monthly_wage = a1950(i1950(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1954: avg_monthly_wage = a1952(i1952(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1956: avg_monthly_wage=a1954(i1954(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1958: avg_monthly_wage = a1956(i1956(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1960: avg_monthly_wage=a1958(i1958(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1961: avg_monthly_wage=a1960(i1960(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1965: avg_monthly_wage=a1961(i1961(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1967: avg_monthly_wage = a1965(i1965(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1969:  avg_monthly_wage = a1967(i1967(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, reference_year, reference_year, woman)
    else: avg_monthly_wage = a1969(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)

    nominal_total_contributions=t1969(adjusted_income_stream, index_year)
    monthly_benefits=bb1969(adjusted_income_stream, original_income_stream, avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)

    nra=65
    if (retirement_year-birth_year)<nra:
        early_deduction=12*(5/9 * .01)*(nra-(retirement_year-birth_year))
        monthly_benefits=(1-early_deduction)*monthly_benefits
    
    return round(monthly_benefits,1)
# pdf page 16 of 1967 pdf no tax change in 1969
def t1969(income_stream:list, index_year:int):
    
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    capped_income_stream=i1969(income_stream, index_year, index_year+len(income_stream)) #to apply the taxable maximums to the benefit stream
    
    for i in range(len(income_stream)): 
        if (index_year+i) <= 1949: #actual tax rates
             employee_tax_rate= 0.01
             employer_tax_rate= 0.01
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1953 and (index_year+i) >=1950: #proposed tax rates onwards
             employee_tax_rate= 0.015
             employer_tax_rate= 0.015
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1958 and (index_year+i) >=1954:
             employee_tax_rate= 0.02
             employer_tax_rate= 0.02
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) == 1959 :
             employee_tax_rate= 0.025
             employer_tax_rate= 0.025
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1961 and income_stream[i] >=1960:
             employee_tax_rate= 0.03
             employer_tax_rate= 0.03
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) == 1962: 
             employee_tax_rate= 0.03125
             employer_tax_rate= 0.03125
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) <=1965 and income_stream[i] >=1963: 
             employee_tax_rate= 0.03625
             employer_tax_rate= 0.03625
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) ==1966: 
             employee_tax_rate= 0.0385
             employer_tax_rate= 0.0385
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1967 and income_stream[i] <=1967: 
             employee_tax_rate= 0.039
             employer_tax_rate= 0.039
        if (index_year+i) >=1968 and income_stream[i] <=1968: 
             employee_tax_rate= 0.038
             employer_tax_rate= 0.038
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1969 and income_stream[i] <=1970: 
             employee_tax_rate= 0.042
             employer_tax_rate= 0.042
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1971 and income_stream[i] <=1972: 
             employee_tax_rate= 0.046
             employer_tax_rate= 0.046
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1973: 
             employee_tax_rate= 0.05
             employer_tax_rate= 0.05
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)

            
    return nominal_contributions



def death1969(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    woman: This is TRUE if the deceased was female.
    '''
    if (q1969(income_stream, index_year, birth_year, retirement_year,woman)): 
        monthlyBenefits = b1969(income_stream, index_year, birth_year, retirement_year,woman)
        return max(3 * monthlyBenefits, 255)
    else:
        return 0

def spouse1969(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    if q1969(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_woman):
        spouse_benefit = b1969(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    primary_adjusted_income_stream=i1969(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1969(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1969(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)
    
    deduction = 1

    if spouse_birth_year + 65 > spouse_retirement_year:
        deduction = deduction - (25/36) * 0.01 * 12 *(spouse_birth_year+65 - spouse_retirement_year)

    spouse_benefit_guarantee = 0.5*primary_PIA *deduction
    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    return round(spousal_benefit,1)




def widow1969(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int,  woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if ((retirement_year >= widow_birth_year +62) or (widow_woman == True and retirement_year >= widow_birth_year +60)) and q1969(income_stream,index_year,birth_year, retirement_year, woman):
        if q1969(widow_income_stream,widow_index_year, widow_birth_year, widow_retirement_year, widow_woman):
            widowMonthlyBenefit = b1969(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_reference_year, widow_woman)
        else: widowMonthlyBenefit = 0
        primary_adjusted_income_stream=i1969(income_stream, index_year, retirement_year)
        primary_avg_monthly_wage = a1969(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman, death_year)
        primaryPIA = bb1969(income_stream,primary_avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)
        

        deduction = 1
        if (widow_woman == True and retirement_year <= widow_birth_year + 62):
            deduction -= (5/9) * 0.01 * 12 * (widow_birth_year + 62 - retirement_year)

        widow_benefit_guarantee = 0.825*primaryPIA  * deduction

        widow_benefit = 0
        if widowMonthlyBenefit < widow_benefit_guarantee:
            widow_benefit = widow_benefit_guarantee - widowMonthlyBenefit

        return math.ceil(widow_benefit * 10) / 10.0
    else:
        return 0

def MFB1969(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1969(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1969(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_avg_monthly_wage = math.floor(primary_avg_monthly_wage)
    #print("avg: ", primary_avg_monthly_wage)

    avg_monthly_wage_list = [
    [0, 76], [76, 78], [78, 80], [80, 81], [81, 83], [83, 85], [85, 87], 
    [87, 89], [89, 90], [90, 92], [92, 94], [94, 96], [96, 97], [97, 99], 
    [99, 101], [101, 102], [102, 104], [104, 106], [106, 107], [107, 109], 
    [109, 113], [113, 118], [118, 122], [122, 127], [127, 132], [132, 136], 
    [136, 141], [141, 146], [146, 150], [150, 155], [155, 160], [160, 164], 
    [164, 169], [169, 174], [174, 178], [178, 183], [183, 188], [188, 193], 
    [193, 197], [197, 202], [202, 207], [207, 211], [211, 216], [216, 221], 
    [221, 225], [225, 230], [230, 235], [235, 239], [239, 244], [244, 249], 
    [249, 253], [253, 258], [258, 263], [263, 267], [267, 272], [272, 277], 
    [277, 281], [281, 286], [286, 291], [291, 295], [295, 300], [300, 305], 
    [305, 309], [309, 314], [314, 319], [319, 323], [323, 328], [328, 333], 
    [333, 337], [337, 342], [342, 347], [347, 351], [351, 356], [356, 361], 
    [361, 365], [365, 370], [370, 375], [375, 379], [379, 384], [384, 389], 
    [389, 393], [393, 398], [398, 403], [403, 407], [407, 412], [412, 417], 
    [417, 421], [421, 426], [426, 431], [431, 436], [436, 440], [440, 445], 
    [445, 450], [450, 454], [454, 459], [459, 464], [464, 468], [468, 473], 
    [473, 478], [478, 482], [482, 487], [487, 492], [492, 496], [496, 501], 
    [501, 506], [506, 510], [510, 515], [515, 520], [520, 524], [524, 529], 
    [529, 534], [534, 538], [538, 543], [543, 548], [548, 553], [553, 556], 
    [556, 560], [560, 563], [563, 567], [567, 570], [570, 574], [574, 577], 
    [577, 581], [581, 584], [584, 588], [588, 591], [591, 595], [595, 598], 
    [598, 602], [602, 605], [605, 609], [609, 612], [612, 616], [616, 620], 
    [620, 623], [623, 627], [627, 630], [630, 634], [634, 637], [637, 641], 
    [641, 644], [644, 648], [648, 650]
    ]

    # Column V: Maximum Family Benefits
    maximum_family_benefits = [
        96.00, 97.50, 99.60, 101.60, 103.40, 105.50, 107.40, 109.20, 111.30, 113.30, 
        115.20, 117.00, 119.10, 121.20, 123.50, 125.30, 127.40, 129.60, 131.70, 133.80, 
        135.90, 137.90, 140.00, 142.10, 144.30, 146.30, 148.20, 150.50, 152.60, 154.50, 
        156.80, 158.70, 160.80, 162.90, 165.00, 167.10, 169.10, 171.30, 173.40, 175.40, 
        177.60, 179.70, 181.50, 183.80, 185.90, 188.00, 190.10, 192.30, 195.20, 199.20, 
        202.40, 206.40, 210.40, 213.60, 217.60, 221.60, 224.80, 228.80, 232.80, 236.00, 
        240.00, 244.00, 247.20, 251.20, 255.20, 258.40, 262.40, 266.40, 269.60, 273.60, 
        277.60, 280.80, 284.80, 288.80, 292.00, 296.00, 300.00, 303.20, 307.20, 311.20, 
        314.40, 318.40, 322.40, 325.60, 329.60, 333.60, 336.80, 340.80, 344.80, 348.80, 
        350.40, 352.40, 354.40, 356.00, 358.00, 360.00, 361.60, 363.60, 365.60, 367.20, 
        369.20, 371.20, 372.80, 374.80, 376.80, 378.40, 380.40, 382.40, 384.00, 386.00, 
        388.00, 389.60, 391.60, 393.60, 395.60, 396.80, 398.40, 399.60, 401.20, 402.40, 
        404.00, 405.20, 406.80, 408.00, 409.60, 410.80, 412.40, 413.60, 415.20, 416.40, 
        418.00, 419.20, 420.80, 422.40, 423.60, 425.20, 426.40, 428.00, 429.20, 430.80, 
        432.00, 433.60, 434.40
    ]

    for i in range(len(avg_monthly_wage_list)):
            if primary_avg_monthly_wage>avg_monthly_wage_list[i][0] and primary_avg_monthly_wage<=avg_monthly_wage_list[i][1]: 
                maximum_family_benefit=maximum_family_benefits[i]


    if maximum_family_benefit: return maximum_family_benefit
    else: return 0


def children1969(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
    """
    This function outputs the children's benefit under the primary's account under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    This function does NOT integrate current entitlement status. This should be done exogenously
    """
    childAge= reference_year - child_birth_year
    if childAge > 22: return 0 #Students between 18-22 can receive Social Security. We assume all applicants are students.
    primary_adjusted_income_stream=i1969(income_stream, index_year, retirement_year)
    if reference_year < death_year:
        primary_avg_monthly_wage = a1969(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    else:
        primary_avg_monthly_wage = a1969(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman, death_year)    
    primary_PIA = bb1969(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)

    if reference_year >= death_year: #If the primary is dead
        return math.ceil(0.75*primary_PIA*10)/10
    else: 
        return math.ceil(0.5* primary_PIA*10)/10