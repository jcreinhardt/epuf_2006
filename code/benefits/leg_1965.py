#!/usr/bin/env python
# coding: utf-8

# In[5]:
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

# updated in pdf page 108-109 of 1965 pdf
def i1965(income_stream:list, index_year:int, retirement_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1952 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy()
    for i in range(len(income_stream)):
        if i+index_year<=1936:
            adjusted_income_stream[i]=0
        if income_stream[i]>3000 and (index_year+i)>1936 and (index_year+i)<1951:
            adjusted_income_stream[i]=3000
        if income_stream[i]>3600 and (index_year+i)>1950 and (index_year+i)<1955:
             adjusted_income_stream[i]=3600
        if income_stream[i]>4200 and (index_year+i)>=1955 and (index_year+i)<=1958:
            adjusted_income_stream[i]=4200
        if income_stream[i]>4800 and (index_year+i)<=1965 and (index_year+i)>=1959:
            adjusted_income_stream[i]=4800      
        if income_stream[i]>6600 and (index_year+i)>=1966:
            adjusted_income_stream[i]=6600 

    return adjusted_income_stream


#there are no changes from 1960, see page pdf page 37 of 1960

def a1965(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, death_year = 0):
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
    index_year = max(index_year ,1951)
    adjusted_income_stream = adjusted_income_stream[startIndex:]
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
        
    drops=5

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
            end_year=birth_year+62 #note that this is different from the previus legislation, "first entitled" now means age 62 in the legislation
        else:
            end_year=birth_year+65
        drops=5
    
        elasped_years=end_year-beginning_year
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

       

    return math.floor(avg_monthly_wage)


#see 1961 pdf page 7, was not update in 1965
def q1965(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int,  retirement_year:int, woman:bool): #this might not be completely correct/ might be off by half a year
    """This function determines whether an individual is considered fully-insured as of the 1950 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, adjusted by the relevant legislation. i1950 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    if q1939(i1939(original_income_stream, index_year, retirement_year), index_year, birth_year, retirement_year, woman): return True
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    startIndex = max(0, 1950-index_year)
    if (retirement_year < birth_year+62): return False
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


    reference_year=max(1951,birth_year+21) #odd nuance of the legislation
    if woman: end_year = birth_year +62
    else: end_year = birth_year+65
    #if woman: end_year = birth_year +62
    #else: end_year = birth_year+65
    #print(coverage_quarters)
    #print(end_year - reference_year)
    if coverage_quarters>40:
        return True
    elif ((coverage_quarters)>=((4/4)*(end_year)-reference_year)) and (coverage_quarters>=6):

        return True
    else:
        return False

def qcurrent1965(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
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

#found on pages 76, 77 of 1965 pdf
def bb1965(adjusted_income_stream:list, original_income_stream:list, avg_monthly_wage:float, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function takes an average monthly wage and calculates the nominal monthly benefit (int) under the 1950 legislation.
        The inputs are (avg_monthly_wage:int, index_year:int, birth_year:int)
        avg_monthly_wage -- the average monthly wage a person received throughout their working history as determined by the 1950 legislation. a1950 will create this value for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
        woman -- gender of recipient, True if a woman
    """
    #initialize variables
    #retirement_year=index_year+len(adjusted_income_stream)
    pia=0
    pib=0 
    pia_1958=0
    

    if (birth_year+65<1950): #this checks if they are old enough to have a pib; someone who did have a pib would receive a new updated pia based on these charts below, if they do they go through the formulas differently. This is what the tables primarily deal with.
        pib=b1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif (birth_year+65<1958):
        if q1958(i1958(original_income_stream, index_year, retirement_year), original_income_stream,  index_year, birth_year, retirement_year, woman): #necessary to make sure b1958 runs
            pia_1958=round(b1958(i1958(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year,woman))

    #These initialize the tables used in the pia formula in the cases of turning 22 before 1950

    pib_list = [
        [0, 13.48], [13.49, 14.00], [14.01, 14.48], [14.49, 15.00], [15.01, 15.60], 
        [15.61, 16.20], [16.21, 16.84], [16.85, 17.60], [17.61, 18.40], [18.41, 19.24], [19.25, 20.00],
        [20.01, 20.64], [20.65, 21.28], [21.29, 21.88], [21.89, 22.28], [22.29, 22.68], [22.69, 23.08], 
        [23.09, 23.44], [23.45, 23.76], [23.77, 24.20], [24.21, 24.60], [24.61, 25.00], [25.01, 25.48],
        [25.49, 25.92], [25.93, 26.40], [26.41, 26.94], [26.95, 27.46], [27.47, 28.00], [28.01, 28.68],
        [28.69, 29.25], [29.26, 29.68], [29.69, 30.36], [30.37, 30.92], [30.93, 31.36], [31.37, 32.00],
        [32.01, 32.60], [32.61, 33.20], [33.21, 33.88], [33.89, 34.50], [34.51, 35.00], [35.01, 35.80],
        [35.81, 36.40], [36.41, 37.08], [37.09, 37.60], [37.61, 38.20], [38.21, 39.12], [39.13, 39.68],
        [39.69, 40.33], [40.34, 41.12], [41.13, 41.76], [41.77, 42.44], [42.45, 43.20], [43.21, 43.76],
        [43.77, 44.44], [44.45, 44.88], [44.89, 45.60]
    ]
    
    
    pia_1958_list=[40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 
     60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 
     80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 
     100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 
     116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127]

    
    pia_list = [
    44.00, 45.00, 46.00, 47.00, 48.00, 49.00, 50.00, 51.00, 52.00, 53.00, 
    54.00, 55.00, 56.00, 57.00, 58.00, 59.00, 60.00, 61.00, 62.10, 63.20, 
    64.20, 65.30, 66.40, 67.50, 68.50, 69.60, 70.70, 71.70, 72.80, 73.90, 
    74.90, 76.00, 77.10, 78.20, 79.20, 80.30, 81.40, 82.40, 83.50, 84.60, 
    85.60, 86.70, 87.80, 88.90, 89.90, 91.00, 92.10, 93.10, 94.20, 95.30, 96.30,
    97.40, 98.50, 99.60, 100.60, 101.70, 102.80, 103.80, 104.90, 106.00, 107.00, 108.10, 
    109.20, 110.30, 111.30, 112.40, 113.50, 114.60, 115.60, 116.70, 117.70, 118.80, 
    119.90, 121.00, 122.00, 123.10, 124.20, 125.20, 126.30, 127.40, 128.40, 129.50, 
    130.60, 131.70, 132.70, 133.80, 134.90, 135.90, 137.00, 138.00, 139.00, 140.00, 
    141.00, 142.00, 143.00, 144.00, 145.00, 146.00, 147.00, 148.00, 149.00, 150.00, 
    151.00, 152.00, 153.00, 154.00, 155.00, 156.00, 157.00, 158.00, 159.00, 160.00,
    161.00, 162.00, 163.00, 164.00, 165.00, 166.00, 167.00, 168.00]

    avg_mon_wage_list = [
        [0, 68],
        [68, 70], [70, 71], [71, 73], [73, 75], [75, 77], [77, 79], [79, 81], [81, 82], [82, 84],
        [84, 86], [86, 88], [88, 90], [90, 91], [91, 93], [93, 95], [95, 97], [97, 98], [98, 100], [100, 102],
        [102, 103], [103, 105], [105, 107], [107, 108], [108, 110], [110, 114], [114, 119], [119, 123], [123, 128],
        [128, 133], [133, 137], [137, 142], [142, 147], [147, 151], [151, 156],
        [156, 161], [161, 165], [165, 170], [170, 175], [175, 179], [179, 184],
        [184, 189], [189, 194], [194, 198], [198, 203], [203, 208], [208, 212],
        [212, 217], [217, 222], [222, 226], [226, 231], [231, 236], [236, 240],
        [240, 245], [245, 250], [250, 254], [254, 259], [259, 264], [264, 268], [268, 273],
        [273, 278], [278, 282], [282, 287], [287, 292], [292, 296], [296, 301],
        [301, 306], [306, 310], [310, 315], [315, 320], [320, 324], [324, 329],
        [329, 334], [334, 338], [338, 343], [343, 348], [348, 352], [352, 357],
        [357, 362], [362, 366], [366, 371], [371, 376], [376, 380], [380, 385],
        [385, 390], [390, 394], [394, 399], [399, 404], [404, 408], [408, 413], [413, 418], [418, 422], [422, 427], 
        [427, 432], [432, 437], [437, 441], [441, 446], [446, 451], 
        [451, 455], [455, 460], [460, 465], [465, 469], [469, 474], 
        [474, 479], [479, 483], [483, 488], [488, 493], [493, 497], 
        [497, 502], [502, 507], [507, 511], [511, 516], [516, 621],
        [521, 525], [525, 530], [530, 535], [535, 539], [539, 544], 
        [544, 549], [549, 100000000000]
    ]

    pia_A=0
    pia_B=0
    pia_C=0

    #print(len(avg_mon_wage_list))
    #print(len(pia_list))
    #actual benefit formula, see note about the spurious "and"
    if ((q1965(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, woman)==True)): #Check if the worker is fully-insured, as well as to place them in the proper formula
        for i in range(len(avg_mon_wage_list)):       
            #print(avg_mon_wage_list[i][0], avg_monthly_wage, avg_mon_wage_list[i][1], pia_list[i])
            if avg_monthly_wage>=avg_mon_wage_list[i][0] and avg_monthly_wage<avg_mon_wage_list[i][1]:
                pia_A=pia_list[i]
    if  (birth_year+65<1950):
        for i in range(len(pib_list)):
            if pib>=pib_list[i][0] and pib<pib_list[i][1]:
                pia_B=pia_list[i]
    if ((q1965(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year,woman)==True) and (birth_year+65<1965)): #They have 1958 pia if they retire before 1965
        for i in range(len(pia_1958_list)):
            if pia_1958==pia_1958_list[i]:
                pia_C=pia_list[i]
    #legislation says to take the maximum of these        
    
    pia=max(pia_A, pia_B, pia_C)

    return pia



# In[ ]:


#output functions are in this cell: bYEAR returns a nominal monthly benefit (int), and tYEAR returns a list of nominal contributions

#total 
def b1965(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        woman -- gender of recipient, True if a woman
    """ 
    #print("hello")
    monthly_benefits=0
    #retirement_year=index_year+len(income_stream)
    adjusted_income_stream=i1965(income_stream, index_year, retirement_year)
    nominal_total_contributions=t1965(income_stream, index_year)
    if retirement_year <= 1950: avg_monthly_wage = a1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1952 : avg_monthly_wage = a1950(i1950(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1954: avg_monthly_wage = a1952(i1952(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1956: avg_monthly_wage=a1954(i1954(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1958: avg_monthly_wage = a1956(i1956(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1960: avg_monthly_wage=a1958(i1958(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1961: avg_monthly_wage=a1960(i1960(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1965: avg_monthly_wage=a1961(i1961(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    else: avg_monthly_wage = a1965(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    monthly_benefits=bb1965(adjusted_income_stream, original_income_stream, avg_monthly_wage, index_year, birth_year,retirement_year, reference_year, woman)

    nra=65
    if (retirement_year-birth_year)<nra:
        early_deduction=12*0.00556*(nra-(retirement_year-birth_year))
        monthly_benefits=(1-early_deduction)*monthly_benefits
    
    return math.ceil(monthly_benefits * 10) / 10.0

# pdf page 110 of 1965 amendment
def t1965(income_stream:list, index_year:int):
    
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    adjusted_income_stream=i1965(income_stream, index_year, index_year + len(income_stream)) #to apply the taxable maximums to the benefit stream
    
    for i in range(len(income_stream)): 
        if (i+index_year) <1937:
             employee_tax_rate= 0.00
             employer_tax_rate= 0.00
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate) 
        if (i+index_year) <= 1949 and (i+index_year)>=1937: #actual tax rates
             employee_tax_rate= 0.01
             employer_tax_rate= 0.01
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1953 and (index_year+i) >=1950: #proposed tax rates onwards
             employee_tax_rate= 0.015
             employer_tax_rate= 0.015
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1956 and (index_year+i) >=1954:
             employee_tax_rate= 0.02
             employer_tax_rate= 0.02
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1958 and (index_year+i) >=1957:
             employee_tax_rate= 0.0225
             employer_tax_rate= 0.0225
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) == 1959 :
             employee_tax_rate= 0.025
             employer_tax_rate= 0.025
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <=1961 and (index_year+i) >=1960:
             employee_tax_rate= 0.03
             employer_tax_rate= 0.03
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <=1962 and (index_year+i) >=1962: 
             employee_tax_rate= 0.03125
             employer_tax_rate= 0.03125
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <=1965 and (index_year+i) >=1963: 
             employee_tax_rate= 0.03625
             employer_tax_rate= 0.03625
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) ==1966: 
             employee_tax_rate= 0.0385
             employer_tax_rate= 0.0385
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1967 and (index_year+i) <=1968: 
             employee_tax_rate= 0.039
             employer_tax_rate= 0.039
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1969 and (index_year+i) <=1972: 
             employee_tax_rate= 0.044
             employer_tax_rate= 0.044
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1973: 
             employee_tax_rate= 0.0485
             employer_tax_rate= 0.0485
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)

            
    return nominal_contributions

def death1965(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    woman: This is TRUE if the deceased was female.
    '''
    if (q1965(income_stream, index_year, birth_year, woman)): 
        monthlyBenefits = b1965(income_stream, index_year, birth_year, retirement_year, woman)
        return max(3 * monthlyBenefits, 255)
    else:
        return 0

def spouse1965(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    if q1965(spouse_income_stream, spouse_index_year, spouse_birth_year,retirement_year, woman):
        spouse_benefit = b1965(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    primary_adjusted_income_stream=i1965(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1965(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1965(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)
    
    deduction = 1

    if spouse_birth_year + 65 > spouse_retirement_year:
        deduction = deduction - (25/36) * 0.01 * 12 *(spouse_birth_year+65 - spouse_retirement_year)

    spouse_benefit_guarantee = 0.5*primary_PIA *deduction

    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    return round(spousal_benefit,1)


def widow1965(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if ((widow_retirement_year >= widow_birth_year +62) or (widow_woman == True and widow_retirement_year >= widow_birth_year +60)) and q1965(income_stream,index_year,birth_year,retirement_year, woman):
        widowMonthlyBenefit = b1965(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_reference_year, widow_woman)
        adjusted_income_stream=i1965(income_stream, index_year, retirement_year)
        avg_monthly_wage = a1965(adjusted_income_stream, index_year, birth_year, retirement_year, reference_year, woman, death_year)
        #print("avg: ", avg_monthly_wage)
        primaryPIA = bb1965(income_stream, avg_monthly_wage,index_year, birth_year,retirement_year, reference_year,woman)
        #print("primary: PIA: ", primaryPIA)

        deduction = 1
        if (widow_woman == True and widow_retirement_year <= widow_birth_year + 62):
            deduction -= (5/9) * 0.01 * 12 * (widow_birth_year + 62 - widow_retirement_year)

        widow_benefit_guarantee = 0.825*primaryPIA  * deduction

        widow_benefit = 0
        if widowMonthlyBenefit < widow_benefit_guarantee:
            widow_benefit = widow_benefit_guarantee - widowMonthlyBenefit

        return math.ceil(widow_benefit * 10) / 10.0
    else:
        return 0
    
def MFB1965(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1965(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1965(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    
    avg_monthly_wage_list = [
        [0, 67], [67, 69], [69, 70], [70, 72], [72, 74], [74, 76], [76, 78], 
        [78, 80], [80, 81], [81, 83], [83, 85], [85, 87], [87, 89], [89, 90], 
        [90, 92], [92, 94], [94, 96], [96, 97], [97, 99], [99, 101], [101, 102], 
        [102, 104], [104, 106], [106, 107], [107, 109], [109, 113], [113, 118], 
        [118, 122], [122, 127], [127, 132], [132, 136], [136, 141], [141, 146], 
        [146, 150], [150, 155], [155, 160], [160, 164], [164, 169], [169, 174], 
        [174, 178], [178, 183], [183, 188], [188, 193], [193, 197], [197, 202], 
        [202, 207], [207, 211], [211, 216], [216, 221], [221, 225], [225, 230], 
        [230, 235], [235, 239], [239, 244], [244, 249], [249, 253], [253, 258], 
        [258, 263], [263, 267], [267, 272], [272, 277], [277, 281], [281, 286], 
        [286, 291], [291, 295], [295, 300], [300, 305], [305, 309], [309, 314], 
        [314, 319], [319, 323], [323, 328], [328, 333], [333, 337], [337, 342], 
        [342, 347], [347, 351], [351, 356], [356, 361], [361, 365], [365, 370], 
        [370, 375], [375, 379], [379, 384], [384, 389], [389, 393], [393, 398], 
        [398, 403], [403, 407], [407, 412], [412, 417], [417, 421], [421, 426], 
        [426, 431], [431, 436], [436, 440], [440, 445], [445, 450], [450, 454], 
        [454, 459], [459, 464], [464, 468], [468, 473], [473, 478], [478, 482], 
        [482, 487], [487, 492], [492, 496], [496, 501], [501, 506], [506, 510], 
        [510, 515], [515, 520], [520, 524], [524, 529], [529, 534], [534, 538], 
        [538, 543], [543, 548], [548, 550]
    ]

    # Column V: Maximum Family Benefits
    maximum_family_benefits = [
        66.00, 67.50, 69.00, 70.50, 72.00, 73.50, 75.00, 76.50, 78.00, 79.50, 
        81.00, 82.50, 84.00, 85.50, 87.00, 88.50, 90.00, 91.50, 93.20, 94.80, 
        96.30, 98.00, 99.60, 101.30, 102.80, 104.40, 106.10, 107.60, 109.20, 
        110.90, 112.40, 114.00, 116.80, 120.00, 124.00, 128.00, 131.20, 135.20, 
        139.20, 142.40, 146.40, 150.40, 154.40, 157.00, 161.60, 165.60, 168.80, 
        172.80, 176.80, 180.00, 184.00, 188.00, 191.20, 195.20, 199.20, 202.40, 
        206.40, 210.40, 213.60, 217.60, 221.60, 224.80, 228.80, 232.80, 236.00, 
        240.00, 244.00, 247.20, 251.20, 255.20, 258.40, 262.40, 266.40, 269.60, 
        273.60, 277.60, 280.80, 284.80, 288.80, 292.00, 296.00, 298.00, 299.60, 
        301.60, 303.60, 305.20, 307.20, 309.20, 310.80, 312.80, 314.80, 316.40, 
        318.40, 320.40, 322.40, 324.00, 326.00, 328.00, 329.60, 331.60, 333.60, 
        335.20, 337.20, 339.20, 340.80, 342.80, 344.80, 346.40, 348.40, 350.40, 
        352.00, 354.00, 356.00, 357.60, 359.60, 361.60, 363.20, 365.20, 367.20, 
        368.00
    ]

    for i in range(len(avg_monthly_wage_list)):
            if primary_avg_monthly_wage>avg_monthly_wage_list[i][0] and primary_avg_monthly_wage<=avg_monthly_wage_list[i][1]: 
                maximum_family_benefit=maximum_family_benefits[i]


    if maximum_family_benefit: return maximum_family_benefit
    else: return 0

def children1965(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
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
    primary_adjusted_income_stream=i1965(income_stream, index_year, retirement_year)
    if reference_year < death_year:
        primary_avg_monthly_wage = a1965(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    else:
        primary_avg_monthly_wage = a1965(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman, death_year)
    primary_PIA = bb1965(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)
    
    
    if reference_year >= death_year: #If the primary is dead
        return math.ceil(0.75*primary_PIA*10)/10
    else: 
        return math.ceil(0.5* primary_PIA*10)/10