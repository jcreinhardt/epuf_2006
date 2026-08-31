#!/usr/bin/env python
# coding: utf-8

# In[7]:


#Daniel Carrillo
#1961 coded legislation

#As a general note, our model operates on a year by year flow of time. The actual Social Security Legislation works on a quarter by quarter flow of time
#This could cause certain distortions. For example, quarters of coverage will probably be overestimated, and periods of unemployment longer than a quarter will not show up in our model
#In our model, all the quarters are scaled to years. For example "the quotient obtained by dividing the total wages paid an individual before the quarter in which he died or became entitled to receive primary insurance benefits"
#Is read as "the quotient obtained by dividing the total wages paid an individual before the YEAR in which he died or became entitled to receive primary insurance benefits"
#As a note, there are no secondary benefits yet, and also maximum benefits have not been coded because those are related to secondary benefits

#also this amendment model currently only works for men, since women have a different retirement age
#We still need to add the drop rule!
#last updated 4/1/25 by DC


# In[2]:
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
import math


#no major updates from 1958, updates to this can be found on pdf page 7 of 1958
def i1961(income_stream:list, index_year:int, retirement_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1952 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy()
    for i in range(len(income_stream)):
        if income_stream[i]>0 and (index_year+i)<=1936:
            adjusted_income_stream[i]=0
        if income_stream[i]>3600 and (index_year+i)<1955 and (index_year+i)>1950:
             adjusted_income_stream[i]=3600
        if income_stream[i]>4200 and (index_year+i)>=1955 and (index_year+i)<=1958:
             adjusted_income_stream[i]=4200
        if income_stream[i]>4800 and (index_year+i)>1958:
            adjusted_income_stream[i]=4800        
    return adjusted_income_stream

def q1961(adjusted_income_stream:list, original_income_stream, index_year:int, birth_year:int,  retirement_year:int, woman:bool): #this might not be completely correct/ might be off by half a year
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
    if birth_year < 62: return False
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
    #end_year = birth_year +62
    #print(coverage_quarters)
    #print(end_year- reference_year)
    if woman: end_year = birth_year +62
    else: end_year = birth_year+65
    if coverage_quarters>=40:
        return True
    elif ((coverage_quarters)>=((4/4)*(end_year)-reference_year)) and (coverage_quarters>=6):
        return True
    else:
        return False


def qcurrent1961(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
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

#there are no changes from 1960, see page pdf page 37 of 1960
def a1961(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, death_year = 0):
    """This function returns the average monthly wage (int) of an individual as determined by the 1952 legislation.
        This is more complicated than one might think, which is why it has its own seperate function.
        The inputs are (adjusted_income_stream:list,index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, adjusted by the relevant legislation. i1952 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream   
        birth_year -- the year the individual is born.
    """    

    #This is the same as the 1965 amendments, the previous iterations are commented below.
    total_wage=0
    avg_monthly_wage_A=0
    avg_monthly_wage_B=0

    # Create a copy of adjusted_income_stream
    adjusted_income_copy = adjusted_income_stream.copy()
    startIndex = max(0, 1951-index_year)
    index_year = max(1951, index_year)
    adjusted_income_copy = adjusted_income_copy[startIndex:]


    numZeros = max(0, index_year -1- 1951)
    adjusted_income_stream = [0] * numZeros + adjusted_income_copy
    

###################
    beginning_year=1951
    if death_year == 0: #This is notation for if the individual has not died yet.
        if woman==True:
            end_year=max(1961, birth_year+62) #note that this is different from the previus legislation, "first entitled" now means age 62 in the legislation
        else:
            end_year=max(1961, birth_year+65)
    else:
        if woman==True:
            end_year=max(1961, min(death_year,birth_year+62)) #note that this is different from the previus legislation, "first entitled" now means age 62 in the legislation
        else:
            end_year=max(1961, min(death_year,birth_year+65))
        
    drops=5
    
    elasped_years=end_year-beginning_year

    #print("elapsed: ", elasped_years)
    
    highest_years=elasped_years-drops
    
    #print("highest: ", highest_years)

    if highest_years<2:
        highest_years=2

    highest_indices = np.argsort(adjusted_income_stream)[-highest_years:] #python is right exclusive
    
    for i in range(len(adjusted_income_stream)): 
        if (i+index_year)>=beginning_year and (i in highest_indices):
            #print(adjusted_income_stream[i])
            # print(i+index_year, " added ", adjusted_income_stream[i])
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
    # Case 2: if you are 22 after 1951 you can use a different forum
    '''if birth_year+22>1950:#the reasoning here is that there is a distinction in the legislation between those who turn 22 before and after 1950.
        #Those who turn 22 after 1950 have the option to use either their age 22 income onward or 1950 income onwards to calculate the average montly wage, the method that maximizes average monthly wage is used automatically
        #Case 2: The starting date is year they turn 22
        beginning_year = birth_year+22 #index_year #AV: On page 30 of the pdf it says the start data is 1951 or when they turn 22, but the earliest start date is 1950
        end_year = index_year + len(adjusted_income_stream)   
        total_wage=0
        count=0
        
        # Calc the total wages between start and end date.
        for i in range(len(adjusted_income_stream)): 
            if (i+index_year)<end_year and (i+index_year)>=beginning_year and (i not in lowest_indices):
                total_wage+=adjusted_income_stream[i]
    
        count = (end_year - beginning_year) - len(lowest_indices)
        avg_monthly_wage_B=total_wage/(max(24,count*12))
        '''
###################

    avg_monthly_wage=max(avg_monthly_wage_A, avg_monthly_wage_B)
    # print("avg: ", avg_monthly_wage)
    return math.floor(avg_monthly_wage)
    
#this was updated from 1960, see 1961 pdf page 7


#found on pages 1, 2, and 3 of 1960 pdf; there are some updates on 1961 pdf page 1
#there is also a 1953 rule I am missing on pdf page 11
def bb1961(adjusted_income_stream:list, original_income_stream:list, avg_monthly_wage:float, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function takes an average monthly wage and calculates the nominal monthly benefit (int) under the 1950 legislation.
        The inputs are (avg_monthly_wage:int, index_year:int, birth_year:int)
        avg_monthly_wage -- the average monthly wage a person received throughout their working history as determined by the 1950 legislation. a1950 will create this value for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    #initialize variables
    pia=0
    pib=0 
    pia_1954=0
    #avg_monthly_wage=a1961(adjusted_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    #avg_monthly_wage = a1958(adjusted_income_stream, index_year, birth_year,retirement_year,woman)
    #print("avg: ", avg_monthly_wage)
    if (retirement_year < birth_year+62): return False
    if (birth_year+65<1950): #this checks if they are old enough to have a pib; someone who did have a pib would receive a new updated pia based on these charts below, if they do they go through the formulas differently. This is what the tables primarily deal with.
        pib=b1939(i1939(original_income_stream, index_year, retirement_year),original_income_stream, index_year, birth_year,retirement_year, reference_year, woman)
    elif (birth_year+65<1958):
        if q1954(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, woman): #Technically not how this works, but we need it
            pia_1954=b1954(i1954(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)

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
    
    
    pia_1954_list=[
        [0, 37.00], [37.10, 38.00], [38.10, 39.00], [39.10, 40.00],
        [40.10, 41.00], [41.10, 42.00], [42.10, 43.00], [43.10, 44.00], [44.10, 45.00], [45.10, 46.00],
        [46.10, 47.00], [47.10, 48.00], [48.10, 49.00], [49.10, 50.00], [50.10, 50.90], [51.00, 51.80],
        [51.90, 52.80], [52.90, 53.70], [53.80, 54.60], [54.70, 55.60], [55.70, 56.50], [56.60, 57.40],
        [57.50, 58.40], [58.50, 59.30], [59.40, 60.20], [60.30, 61.20], [61.30, 62.10], [62.20, 63.00],
        [63.10, 64.00], [64.10, 64.90], [65.00, 65.80], [65.90, 66.80], [66.90, 67.70], [67.80, 68.60],
        [68.70, 69.60], [69.70, 70.50], [70.60, 71.40], [71.50, 72.40], [72.50, 73.30], [73.40, 74.20],
        [74.30, 75.20], [75.30, 76.10], [76.20, 77.10], [77.20, 78.00], [78.10, 78.90], [79.00, 79.90],
        [80.00, 80.80], [80.90, 81.70], [81.80, 82.70], [82.80, 83.60], [83.70, 84.50], [84.60, 85.50], 
        [85.60, 86.40], [86.50, 87.30], [87.40, 88.30], [88.40, 89.20], [89.30, 90.10], [90.20, 91.10],
        [91.20, 92.00], [92.10, 92.90], [93.00, 93.90], [94.00, 94.80], [94.90, 95.80], [95.90, 96.70],
        [96.80, 97.60], [97.70, 98.60], [98.70, 99.50], [99.60, 100.40], [100.50, 101.40], [101.50, 102.30],
        [102.40, 103.20], [103.30, 104.20], [104.30, 105.10], [105.20, 106.00], [106.10, 107.00], [107.10, 107.90],
        [108.00, 108.50]
    ]
    
    
    pia_list=[
        40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
        51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68,
        69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86,
        87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 
        104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127
    ]

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
        [385, 390], [390, 394], [394, 399], [399, 401],
    ]
    

    pia_A=0
    pia_B=0
    pia_C=0
    
    if ((q1961(adjusted_income_stream,original_income_stream, index_year, birth_year,retirement_year,woman)==True)): #Check if the worker is fully-insured, as well as to place them in the proper formula
        for i in range(len(avg_mon_wage_list)):
            if avg_monthly_wage>=avg_mon_wage_list[i][0] and avg_monthly_wage<avg_mon_wage_list[i][1]:
                pia_A=pia_list[i]
    if (birth_year+65<1950): # retire before 1950 under the 1939 law
        for i in range(len(pib_list)):
            if pib>=pib_list[i][0] and pib<pib_list[i][1]:
                pia_B=pia_list[i]
    if  (birth_year+65<1958): # retire before 1958 under the 1954 law
        for i in range(len(pia_1954_list)):
            if pia_1954>=pia_1954_list[i][0] and pia_1954<pia_1954_list[i][1]:
                pia_C=pia_list[i]
    #legislation says to take the maximum of these   
    #print(pia_A, pia_B, pia_C)     
    pia = max(pia_A, pia_B, pia_C)

    return pia
    


## In[ ]:


#output functions are in this cell: bYEAR returns a nominal monthly benefit (int), and tYEAR returns a list of nominal contributions

#total 
def b1961(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """ 
    monthly_benefits=0
    adjusted_income_stream=i1961(income_stream, index_year, retirement_year)
    #nominal_total_contributions=t1961(income_stream, index_year)
    if retirement_year <= 1950: avg_monthly_wage = a1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1952 : avg_monthly_wage = a1950(i1950(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1954: avg_monthly_wage = a1952(i1952(original_income_stream, index_year, retirement_year),original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1956: avg_monthly_wage=a1954(i1954(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1958: avg_monthly_wage = a1956(i1956(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1960: avg_monthly_wage=a1958(i1958(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1961: avg_monthly_wage=a1960(i1960(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    else: avg_monthly_wage=a1961(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    #print("avg: ", avg_monthly_wage)
    monthly_benefits=bb1961(adjusted_income_stream, original_income_stream, avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)
    
    nra=65
    if (retirement_year-birth_year)<nra:
        early_deduction=12*0.00556*(nra-(retirement_year-birth_year))
        monthly_benefits=(1-early_deduction)*monthly_benefits


    return math.ceil(monthly_benefits * 10) / 10.0

#tax rules, found on page 11 of pdf 1961
def t1961(income_stream:list, index_year:int):
    
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    adjusted_income_stream=i1961(income_stream, index_year, index_year + len(income_stream)) #to apply the taxable maximums to the benefit stream
    
    for i in range(len(income_stream)): 
        if (index_year+i) <= 1949: #actual tax rates
             employee_tax_rate= 0.01
             employer_tax_rate= 0.01
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1953 and (index_year+i) >=1950: #proposed tax rates onwards
             employee_tax_rate= 0.015
             employer_tax_rate= 0.015
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1958 & (index_year+i) >=1954:
             employee_tax_rate= 0.02
             employer_tax_rate= 0.02
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
        if (index_year+i) <=1967 and (index_year+i) >=1966: 
             employee_tax_rate= 0.04125
             employer_tax_rate= 0.04125
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1968: 
             employee_tax_rate= 0.04625
             employer_tax_rate= 0.04625
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
            
    return nominal_contributions

def death1961(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    '''
    if (q1961(income_stream, index_year, birth_year, retirement_year,woman)): 
        monthlyBenefits = b1961(income_stream, index_year, birth_year)
        return max(3 * monthlyBenefits, 255)
    else:
        return 0

def spouse1961(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    if q1961(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_woman):
        spouse_benefit = b1961(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    primary_adjusted_income_stream=i1961(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1961(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1961(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)
    
    deduction = 1

    if spouse_birth_year + 65 > spouse_retirement_year:
        deduction = deduction - (25/36) * 0.01 * 12 *(spouse_birth_year+65 - spouse_retirement_year)

    spouse_benefit_guarantee = 0.5*primary_PIA *deduction

    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    return spousal_benefit


def widow1961(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if (widow_retirement_year >= widow_birth_year +62) and q1961(income_stream,index_year,birth_year, retirement_year,woman):
        if q1961(widow_income_stream,widow_index_year, widow_birth_year, widow_retirement_year, woman):
            widowMonthlyBenefit = b1961(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_reference_year, widow_woman)
        else: widowMonthlyBenefit = 0
        primary_adjusted_income_stream=i1961(income_stream, index_year, retirement_year)
        primary_avg_monthly_wage = a1961(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman, death_year)
    
        primaryPIA = bb1961(income_stream,primary_avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)
        
        
        widow_benefit_guarantee = 0.825*primaryPIA 

        widow_benefit = 0
        if widowMonthlyBenefit < widow_benefit_guarantee:
            widow_benefit = widow_benefit_guarantee - widowMonthlyBenefit

        return math.ceil(widow_benefit * 10) / 10.0
    else:
        return 0
    

def MFB1961(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1961(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1961(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)

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
    [398, 400]]

    # Column V: Maximum Family Benefits
    maximum_family_benefits = [
         60.0, 61.5, 63.0, 64.5, 66.4, 
        67.5, 69.0, 70.5, 72.0, 73.5, 75.0, 76.5, 78.0, 79.5, 81.0, 82.5, 84.0, 
        85.5, 87.0, 88.5, 90.0, 91.5, 93.0, 94.5, 96.0, 97.5, 99.0, 100.5, 102.0, 
        105.6, 108.8, 112.8, 116.8, 120.0, 124.0, 128.0, 131.2, 135.2, 139.2, 
        142.4, 146.4, 150.4, 154.4, 157.6, 161.6, 165.6, 168.8, 172.8, 176.8, 
        180.0, 184.0, 188.0, 191.2, 195.2, 199.2, 202.4, 206.4, 210.4, 213.6, 
        217.6, 221.6, 224.8, 228.8, 232.8, 236.0, 240.0, 244.0, 247.2, 251.2, 
        254.0, 254.0, 254.0, 254.0, 254.0, 254.0, 254.0, 254.0, 254.0, 254.0, 
        254.0, 254.0, 254.0, 254.0, 254.0, 254.0, 254.0, 254.0, 254.0
    ]

    for i in range(len(avg_monthly_wage_list)):
            #print(avg_monthly_wage_list[i][0], primary_avg_monthly_wage, avg_monthly_wage_list[i][1])
            if primary_avg_monthly_wage>avg_monthly_wage_list[i][0] and primary_avg_monthly_wage<=avg_monthly_wage_list[i][1]: 
                maximum_family_benefit=maximum_family_benefits[i]


    if maximum_family_benefit: return maximum_family_benefit
    else: return 0

def children1961(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
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
    if childAge > 18: return 0
    primary_adjusted_income_stream=i1961(income_stream, index_year, retirement_year)
    if reference_year < death_year:
        primary_avg_monthly_wage = a1961(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    else:
        primary_avg_monthly_wage = a1961(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman, death_year)
    primary_PIA = bb1961(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)

    if reference_year >= death_year: #If the primary is dead
        return math.ceil(0.75*primary_PIA*10)/10
    else: 
        return math.ceil(0.5* primary_PIA*10)/10