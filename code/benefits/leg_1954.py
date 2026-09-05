#!/usr/bin/env python
# coding: utf-8

# In[4]:


#Daniel Carrillo
#1954 coded legislation

#As a general note, our model operates on a year by year flow of time. The actual Social Security Legislation works on a quarter by quarter flow of time
#This could cause certain distortions. For example, quarters of coverage will probably be overestimated, and periods of unemployment longer than a quarter will not show up in our model
#In our model, all the quarters are scaled to years. For example "the quotient obtained by dividing the total wages paid an individual before the quarter in which he died or became entitled to receive primary insurance benefits"
#Is read as "the quotient obtained by dividing the total wages paid an individual before the YEAR in which he died or became entitled to receive primary insurance benefits"
#As a note, there are no secondary benefits yet, and also maximum benefits have not been coded because those are related to secondary benefits

#there's several minor things I am missing, I'll need to go over this one more time, maybe with someone helping me
#last updated 3/25/25 by DC


# In[ ]:


#iYEAR, aYEAR, qYEAR, and bbYEAR are all intermediate functions that are called within the main output functions in the next cell
import numpy as np
import time
from leg_1939 import *
from leg_1952 import *
import math 

#pdf page 27 of 1954 amendments, this needs a better citation
def i1954(income_stream:list, index_year:int, retirement_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1952 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy()
    for i in range(len(income_stream)):
        if i+index_year<=1950:
            adjusted_income_stream[i]=0
        if income_stream[i]>3600 and (index_year+i)>1950 and (index_year+i)<1955:
             adjusted_income_stream[i]=3600
        if income_stream[i]>4200 and (index_year+i)>=1955:
             adjusted_income_stream[i]=4200
        if income_stream[i]>3000 and (index_year+i)<1951:
            adjusted_income_stream[i]=3000
    return adjusted_income_stream

#the legislation can be found on page 11 and 12 of 1954 pdf. It doesn't seem like there are any changes, so it might require a closer look

def a1954(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function returns the average monthly wage (int) of an individual as determined by the 1952 legislation.
        This is more complicated than one might think, which is why it has its own seperate function.
        The inputs are (adjusted_income_stream:list,index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, adjusted by the relevant legislation. i1952 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream   
        birth_year -- the year the individual is born.
    """   


    #initializing
    total_wage_entitlement=0
    total_wage_qualification=0
    avg_monthly_wage_A=0
    avg_monthly_wage_B=0

    # Create a copy of adjusted_income_stream
    adjusted_income_copy = adjusted_income_stream.copy()
    startIndex = max(0, 1951-index_year)
    adjusted_index_year = max(index_year ,1951)
    adjusted_income_stream = adjusted_income_stream[startIndex:]
    ###################

    #Case 1: The starting date is 1950, we initially coded this wrong, post 1961 version, years after age 62 don't count for elapsed years purposes
    beginning_year=1951
    end_year=retirement_year #This is also the year of qualificaiton, if that would be higher.
    coverage_quarters = 0

    nra = 65 
    ageAtIndex = adjusted_index_year - birth_year
    if nra - ageAtIndex+1 >= 0:
        qualificationInc = adjusted_income_stream[0:nra - ageAtIndex+1]
    else:
        qualificationInc =[]
    while not q1954(qualificationInc, original_income_stream, index_year, birth_year, retirement_year, woman):
        nra +=1
        if nra - ageAtIndex+1 >= 0:
            qualificationInc = adjusted_income_stream[0:nra - ageAtIndex+1]
        else:
            qualificationInc =[]
    qualification_year = birth_year + nra 

    for i in range(len(adjusted_income_stream)):
        if adjusted_income_stream[i]>=200:
            coverage_quarters+=4
        elif adjusted_income_stream[i] >= 150:
            coverage_quarters +=3
        elif adjusted_income_stream[i] >= 100:
            coverage_quarters +=2
        elif adjusted_income_stream[i] >= 50:
            coverage_quarters +=1
        
        if coverage_quarters >= 20:
            drops=5
        else:
            drops = 4
    elasped_years=end_year-beginning_year

    highest_years_entitlement=elasped_years-drops
    highest_years_qualification = qualification_year - beginning_year - drops
    
    

    if highest_years_entitlement<2:
        highest_years_entitlement=2
    if highest_years_qualification<2:
        highest_years_qualification=2
    
    #print(highest_years)

    highest_indices_entitlement = np.argsort(adjusted_income_stream)[-highest_years_entitlement:] #python is right exclusive
    highest_indices_qualification = np.argsort(adjusted_income_copy)[-highest_years_qualification:]
    for i in range(len(adjusted_income_stream)): 
        if (i+index_year)>=beginning_year and (i in highest_indices_entitlement):
            total_wage_entitlement+=adjusted_income_stream[i]
    
    for i in range(len(adjusted_income_stream)): 
        if (i+index_year)>=beginning_year and (i in highest_indices_qualification):
            total_wage_qualification+=adjusted_income_stream[i]

    count = highest_years_entitlement 
    yrBefore22andNotCovered = 0
    yr_22 = birth_year + 22

    count = count - yrBefore22andNotCovered 
    avg_monthly_wage_A= max(total_wage_entitlement/(max(24,count*12)), total_wage_qualification/(max(24,(highest_years_qualification)*12)))
###################
    # Case 2: if you are born after 1951 you can use a different forum
    if birth_year+22>1950:#the reasoning here is that there is a distinction in the legislation between those who turn 22 before and after 1950.
        #Those who turn 22 after 1950 have the option to use either their age 22 income onward or 1950 income onwards to calculate the average montly wage, the method that maximizes average monthly wage is used automatically
        #Case 2: The starting date is year they turn 22
        beginning_year=1951
        end_year=birth_year+65
        
        coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
        for i in range(len(adjusted_income_stream)):
            if adjusted_income_stream[i]>=200:
                coverage_quarters+=4
            elif adjusted_income_stream[i] >= 150:
                coverage_quarters +=3
            elif adjusted_income_stream[i] >= 100:
                coverage_quarters +=2
            elif adjusted_income_stream[i] >= 50:
                coverage_quarters +=1
            
            if coverage_quarters >= 20:
                drops=5
            else:
                drops = 4
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

#assuming that this is same as 1950 version, could be checked more
def q1954(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int,  retirement_year:int, woman:bool): #this might not be completely correct/ might be off by half a year
    """This function determines whether an individual is considered fully-insured as of the 1950 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1950 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    # print("="*16)
    if original_income_stream == []: original_income_stream = adjusted_income_stream #Band-aid until I finish this later.   
    # print("original: ", adjusted_income_stream)
    # print(original_income_stream, index_year, retirement_year, birth_year, woman)
    if q1939(i1939(original_income_stream, index_year, retirement_year), index_year, birth_year, retirement_year, woman): 
        # print("Q1939 Passed Successfully")
        # print("True - q")
        return True
    # else:
        # print("False")
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    startIndex = max(0, 1951- index_year)
    # print(startIndex, index_year)


    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    for i in range(startIndex, len(adjusted_income_stream)):
        # print(i, " ", adjusted_income_stream[i])
        if adjusted_income_stream[i]>=200:
            coverage_quarters+=4
        elif adjusted_income_stream[i] >= 150:
            coverage_quarters +=3
        elif adjusted_income_stream[i] >= 100:
            coverage_quarters +=2
        elif adjusted_income_stream[i] >= 50:
            coverage_quarters +=1
    reference_year=max(1951,birth_year+21) #odd nuance of the legislation
    
    if woman: end_year = birth_year +62
    else: end_year = birth_year+65

    # print("coverage: ", coverage_quarters)
    # print("required: ", 2* (end_year-reference_year))


    if coverage_quarters>40:
        # print("true")
        return True
    elif (2*(coverage_quarters/4)>=(end_year)-reference_year) and (coverage_quarters>=6):
        # print("true")
        return True
    else:
        # print("false")
        return False


def qcurrent1954(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
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

def b1952helper(adjusted_income_stream:list, index_year:int, retirement_year:int, birth_year:int):
    """This function returns the average monthly wage (int) of an individual as determined by the 1952 legislation.
        This is more complicated than one might think, which is why it has its own seperate function.
        The inputs are (adjusted_income_stream:list,index_year:int, bith_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1952 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream   
        birth_year -- the year the individual is born.
    """    
    avg_monthly_wage_A=0
    avg_monthly_wage_B=0
    
#Case 1: The starting date is 1950
    beginning_year = 1951 #index_year #AV: On page 30 of the pdf it says the start data is 1951 or when they turn 22, but the earliest start dat is 1950
    end_year = retirement_year
    #end_year = birth_year+65 
    #if end_year <= beginning_year: #If the individual turned 65 before 1951 but retired late, after 1951
    #    end_year = retirement_year
    total_wage=0
    count=0

    for i in range(len(adjusted_income_stream)): 
        if (i+index_year) <= end_year and (i+index_year)>=beginning_year :
            #print(i + index_year, " added ", adjusted_income_stream[i])
            total_wage+=adjusted_income_stream[i]
    
    #end_year = birth_year+65 
        count = (end_year - beginning_year+1)
    
    #print(count)
    yrBefore22andNotCovered = 0
    yr_22 = birth_year + 22

    if yr_22 > beginning_year:
        for i in range(beginning_year,yr_22): # Go through all years they are < 22 age
            #print("hello: ", i - index_year)
            #print(adjusted_income_stream)
            if (i-index_year) > 0 and adjusted_income_stream[i-index_year]<200: # Check that it is a valid income index and they make less than 200. 
                yrBefore22andNotCovered += 1 # Add one to not covered

    count = count - yrBefore22andNotCovered

    avg_monthly_wage_A= math.floor(total_wage/(max(18,count*12)))
    yrBefore22andNotCovered = 0
    yr_22 = birth_year + 22

    #print(avg_monthly_wage_A)

# Case 2: if you are born after 1951 you can use a different forum
    if birth_year+22>1950:#the reasoning here is that there is a distinction in the legislation between those who turn 22 before and after 1950.
                            #Those who turn 22 after 1950 have the option to use either their age 22 income onward or 1950 income onwards to calculate the average montly wage, the method that maximizes average monthly wage is used automatically
         #Case 2: The starting date is year they turn 22
        beginning_year = birth_year+22 #index_year #AV: On page 30 of the pdf it says the start data is 1951 or when they turn 22, but the earliest start date is 1950
        end_year = index_year + len(adjusted_income_stream)   
        total_wage=0
        count=0
    
        # Calc the total wages between start and end date.
        for i in range(len(adjusted_income_stream)): 
            if (i+index_year)<end_year and (i+index_year)>=beginning_year:
                total_wage+=adjusted_income_stream[i]
    
        count = (end_year - beginning_year)
        #print("the count is ", count)
        avg_monthly_wage_B=total_wage/(max(18,count*12))
        
    avg_monthly_wage=math.floor(max(avg_monthly_wage_A, avg_monthly_wage_B))
    
    #print("the average monthly wage is ", avg_monthly_wage)

    pia=0
    

    
    pia_list=[25.00, 27.00, 29.00, 31.00, 33.00, 35.00, 36.70, 38.20, 39.50, 40.70, 42.00, 43.50, 45.30, 
              47.50, 50.10, 52.40, 54.40, 56.30, 58.00, 59.40, 60.80, 62.00, 63.30, 64.40, 65.50, 
              66.60, 67.80, 68.90, 70.00, 71.00, 72.00, 73.10, 74.10, 75.10, 76.10, 77.10, 77.10,]
    
    average_monthly_wage_list=[45.00, 49.00, 53.00, 56.00, 60.00, 64.00, 67.00, 69.00, 72.00, 74.00, 76.00, 79.00, 82.00, 86.00, 
                               91.00, 95.00, 99.00, 109.00, 109.00, 120.00, 129.00, 139.00, 147.00, 155.00, 163.00, 170.00, 
                               177.00, 185.00, 193.00, 200.00, 207.00, 213.00, 221.00, 227.00, 234.00, 241.00, 250.00, 250.00]

    
    if ((birth_year+22>=1951)):
        if avg_monthly_wage>=48:
            pia=(.55*min(avg_monthly_wage,100))+max((.15*min(avg_monthly_wage-100,200)),0)
        elif avg_monthly_wage<48 and avg_monthly_wage>=35:
            pia=26
        elif avg_monthly_wage<35:
            pia=25
            
    elif((birth_year+22<1951)):
        if avg_monthly_wage>=48:
            pia=(.55*min(avg_monthly_wage,100))+max((.15*min(avg_monthly_wage-100,200)),0)
        elif avg_monthly_wage<48 and avg_monthly_wage>=35:
            pia=26
        elif avg_monthly_wage<35:
            pia=25

        
    else:
        #checking what they would get if their pia's were simply updated from pib
        #print("hello")
        pia=0
    
    #print("the pia: ", pia)
    return pia

def b1939helper(income_stream:list, index_year:int, birth_year:int, retirement_year:int, woman:bool):
    """This function determines whether an individual is considered fully-insured as of the 1939 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """   
    total_wage=0
    count=0
    adjusted_income_stream=i1939(income_stream, index_year, retirement_year)
    yearOfQual = 0
    for year in range(index_year, index_year + len(income_stream)):
        incomeStream = []
        for i, income in enumerate(income_stream):
            if i + index_year <= year: incomeStream.append(income)
        if q1954(incomeStream, index_year, birth_year,retirement_year, woman) and yearOfQual  == 0: yearOfQual = year
    
    if yearOfQual == 0: 
        return 0
    count = 12*(yearOfQual - index_year)
    
    for i in range(len(adjusted_income_stream)):
        if (i+index_year>1936) and not (i+index_year-22<0 and adjusted_income_stream[i]<200) and ( i + index_year <= yearOfQual): #there's something else here, check @Daniel
            total_wage+=adjusted_income_stream[i]
    if count==0:
        avg_monthly_wage=0
    else: 

        avg_monthly_wage=total_wage/(count*12)
    avg_monthly_wage=int(avg_monthly_wage)
    
    #print("the average monthly wage is ", avg_monthly_wage)

    adjusted_income_stream=i1939(income_stream, index_year, retirement_year)
    
    if avg_monthly_wage<50:
        pia_partA=.4*avg_monthly_wage 
    else:
        if avg_monthly_wage>250: 
            avg_monthly_wage=250
        pia_partA=(.4*50)+(.1*(avg_monthly_wage-50))
        
    count=0 
    for i in range(len(adjusted_income_stream)):
        if adjusted_income_stream[i]>=200:
            count+=1
    benefit=pia_partA+(.01*pia_partA*count) 
    if benefit<10:
        benefit=10
        
    return benefit 


#found on pages 11 and 12 of pdf; these are very complicated and arcane. I doubt that, as of feb 5 2025, they are completely correc. Of particular concern is the paragraph immediately following the table
#benefit rules
#there is also a 1953 rule I am missing on pdf page 11
def bb1954(adjusted_income_stream:list, original_income_stream:list, avg_monthly_wage:float, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function takes an average monthly wage and calculates the nominal monthly benefit (int) under the 1950 legislation.
        The inputs are (avg_monthly_wage:int, index_year:int, birth_year:int)
        avg_monthly_wage -- the average monthly wage a person received throughout their working history as determined by the 1950 legislation. a1950 will create this value for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    #initialize variables
    pia=0
    pib=0 
    pia_1952=0
    #avg_monthly_wage=a1954(adjusted_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    #print("avg: ", avg_monthly_wage)
    if (birth_year+65<1950 and q1939(i1939(original_income_stream, index_year, retirement_year), index_year, birth_year,retirement_year, woman)):# and index_year <= 1950): #this checks if they are old enough to have a pib; someone who did have a pib would receive a new updated pia based on these charts below, if they do they go through the formulas differently. This is what the tables primarily deal with.
        pib = b1939(adjusted_income_stream, original_income_stream, index_year, birth_year,retirement_year, reference_year, woman)
    pia_1952=b1952helper(adjusted_income_stream, index_year, retirement_year, birth_year)

    #print(pia_1952)
    
    pib_list=[10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 
         22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 
         34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]
    
    pia_1952_list = [
        [25.00, 27.00], [27.00, 29.00], [29.00, 31.00], [31.00, 33.00], [33.00, 35.00], [35.00, 36.70],
        [36.70, 38.20], [38.20, 39.50], [39.50, 40.70], [40.70, 42.00], [42.00, 43.50], [43.50, 45.30],
        [45.30, 47.50], [47.50, 50.10], [50.10, 52.40], [52.40, 54.40], [54.40, 56.30], [56.30, 58.00],
        [58.00, 59.40], [59.40, 60.80], [60.80, 62.00], [62.00, 63.30], [63.30, 64.40], [64.40, 65.50],
        [65.50, 66.60], [66.60, 67.80], [67.80, 68.90], [68.90, 70.00], [70.00, 71.00], [71.00, 72.00],
        [72.00, 73.10], [73.10, 74.10], [74.10, 75.10], [75.10, 76.10], [76.10, 77.10], [77.10, 77.20],
        [77.20, 77.30], [77.30, 77.40], [77.40, 77.50], [77.50, 78.00], [78.00, 79.00], [79.00, 80.10],
        [80.10, 81.00], [81.00, 82.00], [82.00, 83.10], [83.10, 84.00], [84.00, 85.00], [85.00, 86.00]
    ]
  
    pia_list=[30.00, 32.00, 34.00, 36.00, 38.00, 40.00, 41.70, 43.20, 44.50, 45.70, 47.00, 48.50, 
     50.30, 52.50, 55.10, 57.40, 59.40, 61.30, 63.00, 64.40, 66.30, 67.90, 69.50, 71.10, 
     72.50, 73.90, 75.50, 77.10, 78.50, 79.90, 81.10, 82.70, 83.90, 85.30, 86.70, 88.50, 88.50, 
     88.50, 88.50, 88.50, 88.50, 89.10, 90.50, 91.90, 93.10, 94.50, 95.90, 97.10, 98.50, 
     98.50, 98.50]

    pia_A=0
    pia_B=0
    pia_C=0
    #actual benefit formula

    if retirement_year == 1954: return bb1952(adjusted_income_stream, original_income_stream, avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)

    if ((q1954(adjusted_income_stream, original_income_stream, index_year, birth_year,retirement_year, woman)==True)) : #and not qualifiedBefore1954:#and (birth_year+65>1954)): #Check if the worker is fully-insured, as well as to place them in the proper formula
        pia_A=(.55*min(avg_monthly_wage,110))+max((.20*min(avg_monthly_wage-110,240)),0)
        qa1939 = False
    
    if ((q1954(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year,woman)==True)):# and not qualifiedBefore1954 < 6:#and (birth_year+65>1954)):
        for i in range(len(pia_1952_list)):
            if pia_1952>=pia_1952_list[i][0] and pia_1952<=pia_1952_list[i][1]:
                pia_C=pia_list[i]
        qa1939 = False

    if ((q1954(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year,woman)==True)): #and (index_year<=1954)) or qa1939:
        #print("i'm here ", pib)
        for i in range(2, len(pib_list)):
            if pib >= pib_list[i-1] and pib <= pib_list[i]:
                pia_B = pia_list[i-1] + (pia_list[i] - pia_list[i-1])*(pib - pib_list[i-1])
    


    pia=max(pia_A, pia_B, pia_C)
    return pia
        
            

# In[ ]:


#output functions are in this cell: bYEAR returns a nominal monthly benefit (int), and tYEAR returns a list of nominal contributions

#y1950 beginning and end year on page 30 of pdf
def b1954(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """ 
    monthly_benefits=0
    adjusted_income_stream=i1954(income_stream, index_year, retirement_year)
    # index_year = 
    nominal_total_contributions=t1954(income_stream, index_year)

    if retirement_year <= 1950: avg_monthly_wage = a1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1952 : avg_monthly_wage = a1950(i1950(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1954: avg_monthly_wage = a1952(i1952(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    else: avg_monthly_wage=a1954(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)

    retirement_age=retirement_year-birth_year
    if retirement_age>=65:
        monthly_benefits=bb1954(adjusted_income_stream, original_income_stream, avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)
    
    
    return round(monthly_benefits,1)
    
#tax rules pdf page 43
def t1954(income_stream:list, index_year:list):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """     
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    adjusted_income_stream=i1954(income_stream, index_year, index_year + len(income_stream))
    
    for i in range(len(adjusted_income_stream)): 
        if (i+index_year) <1937:
             employee_tax_rate= 0.00
             employer_tax_rate= 0.00
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate) 
        if (i+index_year) <= 1949 and (i+index_year>=1937): #actual tax rates
             employee_tax_rate= 0.01
             employer_tax_rate= 0.01
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1954 and (i+index_year)>=1950: #proposed tax rates onwards
             employee_tax_rate= 0.015
             employer_tax_rate= 0.015
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1959 and (index_year+i) >= 1955: #actual tax rates
             employee_tax_rate= 0.02
             employer_tax_rate= 0.02
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1964 and (index_year+i) >=1960: #proposed tax rates onwards
             employee_tax_rate= 0.025
             employer_tax_rate= 0.025
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1969 & (index_year+i) >=1965:
             employee_tax_rate= 0.03
             employer_tax_rate= 0.03
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1974 & (index_year+i) >=1970:
             employee_tax_rate= 0.035
             employer_tax_rate= 0.035
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1975:
             employee_tax_rate= 0.04
             employer_tax_rate= 0.04
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)

            
    return nominal_contributions

def death1954(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    '''
    if (q1954(income_stream, index_year, birth_year, retirement_year,woman)): 
        monthlyBenefits = b1954(income_stream, index_year, birth_year, retirement_year)
        return max(3 * monthlyBenefits, 255)
    else:
        return 0


def spouse1954(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    if q1954(spouse_income_stream, spouse_index_year, spouse_birth_year, retirement_year,woman):
        spouse_benefit = b1954(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    primary_adjusted_income_stream=i1954(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1954(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1954(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)

    spouse_benefit_guarantee = 0.5*primary_PIA 

    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    return spousal_benefit


def widow1954(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if widow_retirement_year >= widow_birth_year + 65 and q1954(income_stream,index_year,birth_year,retirement_year, woman):
        if q1954(widow_income_stream,widow_index_year, widow_birth_year, widow_retirement_year, widow_woman):
            widowMonthlyBenefit = b1954(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_reference_year, widow_woman)
        else: widowMonthlyBenefit = 0
        primary_adjusted_income_stream=i1954(income_stream, index_year, retirement_year)
        primary_avg_monthly_wage = a1954(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    
        primaryPIA = bb1954(income_stream,primary_avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)
        widow_benefit_guarantee = 0.75*primaryPIA 

        widow_benefit = 0
        if widowMonthlyBenefit < widow_benefit_guarantee:
            widow_benefit = widow_benefit_guarantee - widowMonthlyBenefit

        return round(widow_benefit,1)
    else:
        return 0
    
def MFB1954(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1954(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1954(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primaryMonthlyBenefit = b1954(primary_adjusted_income_stream, index_year, birth_year, retirement_year, reference_year, woman)

    maximumFamilyBenefit = min(200, max(50, 1.5 * primaryMonthlyBenefit, .8* primary_avg_monthly_wage))
    return maximumFamilyBenefit


def children1954(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
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
    primary_adjusted_income_stream=i1954(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1954(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1954(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)

    return math.ceil(0.5* primary_PIA *10)/10