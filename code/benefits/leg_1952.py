#!/usr/bin/env python
# coding: utf-8

# In[4]:


#Daniel Carrillo
#1952 coded legislation

#As a general note, our model operates on a year by year flow of time. The actual Social Security Legislation works on a quarter by quarter flow of time
#This could cause certain distortions. For example, quarters of coverage will probably be overestimated, and periods of unemployment longer than a quarter will not show up in our model
#In our model, all the quarters are scaled to years. For example "the quotient obtained by dividing the total wages paid an individual before the quarter in which he died or became entitled to receive primary insurance benefits"
#Is read as "the quotient obtained by dividing the total wages paid an individual before the YEAR in which he died or became entitled to receive primary insurance benefits"
#As a note, there are no secondary benefits yet, and also maximum benefits have not been coded because those are related to secondary benefits

#This legislation is very similiar to the 1950 amendment version. It seems that only the pia formula and table were changed

#last updated 3/25/25 by DC


# In[5]:


#iYEAR, aYEAR, qYEAR, and bbYEAR are all intermediate functions that are called within the main output functions in the next cell

import numpy as np
from leg_1939 import *
from leg_1950 import *
import math

#same as 1950, see page 17 of 1950 pdfs
def i1952(income_stream:list, index_year:int, retirement_year:int):
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
        if income_stream[i]>3600 and (index_year+i)>1950 and (index_year+i)<1955:
             adjusted_income_stream[i]=3600
        if income_stream[i]>3000 and (index_year+i)<1951:
            adjusted_income_stream[i]=3000
    return adjusted_income_stream



#average monthly wage calculator
#as far as I (DC) can tell, this is identical to the 1950 version
def a1952(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function returns the average monthly wage (int) of an individual as determined by the 1952 legislation.
        This is more complicated than one might think, which is why it has its own seperate function.
        The inputs are (adjusted_income_stream:list,index_year:int, bith_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1952 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream   
        birth_year -- the year the individual is born.
    """    

    startIndex = max(0, 1951-index_year)
    index_year = max(index_year ,1951)
    adjusted_income_stream = adjusted_income_stream[startIndex:]
    
    avg_monthly_wage_A=0
    avg_monthly_wage_B=0
    
#Case 1: The starting date is 1950
    beginning_year = 1951 #index_year #AV: On page 30 of the pdf it says the start data is 1951 or when they turn 22, but the earliest start dat is 1950
    
    nra = 65 
    ageAtIndex = index_year - birth_year
    if nra - ageAtIndex+1 >= 0:
        qualificationInc = adjusted_income_stream[0:nra - ageAtIndex+1]
    else:
        qualificationInc =[]
    while not q1952(qualificationInc, original_income_stream, index_year, birth_year, retirement_year, woman, original_income_stream):
        nra +=1
        if nra - ageAtIndex+1 >= 0:
            qualificationInc = adjusted_income_stream[0:nra - ageAtIndex+1]
        else:
            qualificationInc =[]
    
    end_year = retirement_year #nra + birth_year

    qualification_year = birth_year + nra 

    #print("qualification year: ", qualification_year)

    entitlement_total_wage = 0

    # Calc the total wages between start and end date.
    startIndex = max(0, 1950-index_year)
    for i in range(startIndex, len(adjusted_income_stream)): 
        if (i+index_year) <= end_year and (i+index_year)>=beginning_year :
            entitlement_total_wage+=adjusted_income_stream[i]
    
    #end_year = birth_year+65 
    count = (end_year - beginning_year)

    qualification_total_wage = 0
    for i in range(len(adjusted_income_stream)): 
        #print("====", i+index_year, qualification_year)
        if (i+index_year) <= qualification_year and (i+index_year)>=beginning_year :
            qualification_total_wage+=adjusted_income_stream[i]
    yrBefore22andNotCovered = 0
    yr_22 = birth_year + 22

    if yr_22 > beginning_year:
        for i in range(beginning_year,yr_22): # Go through all years they are < 22 age
            if (i-index_year) > 0 and adjusted_income_stream[i-index_year]<200: # Check that it is a valid income index and they make less than 200. 
                yrBefore22andNotCovered += 1 # Add one to not covered

    count = count - yrBefore22andNotCovered
    #print("the count is ", count)
    #print("total: ", entitlement_total_wage)
    avg_monthly_wage_entitlement= math.floor(entitlement_total_wage/(max(18,count*12)))

    #print("qual total: ", qualification_total_wage)
    #print("the count is: ",  12 * (qualification_year - beginning_year))
    avg_monthly_wage_retirement = math.floor(qualification_total_wage)/max(18, 12 * (qualification_year - beginning_year+1))

    avg_monthly_wage_A = max(avg_monthly_wage_entitlement, avg_monthly_wage_retirement)
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
        startIndex = max(0, 1950-index_year)
        for i in range(startIndex, len(adjusted_income_stream)): 
            if (i+index_year)<end_year and (i+index_year)>=beginning_year:
                total_wage+=adjusted_income_stream[i]
    
        count = (end_year - beginning_year)
        
        avg_monthly_wage_B=total_wage/(max(18,count*12))
        
    avg_monthly_wage=max(avg_monthly_wage_A, avg_monthly_wage_B)
    
    #print("the average monthly wage is ", avg_monthly_wage)

    return avg_monthly_wage

#there seems to be no change from the 1950 version here
def q1952(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, woman:bool): #this might not be completely correct/ might be off by half a year
    """This function determines whether an individual is considered fully-insured as of the 1950 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1950 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    if original_income_stream == []: original_income_stream = adjusted_income_stream #Band-aid until I finish this later.
    if q1939(i1939(original_income_stream, index_year, retirement_year), index_year, birth_year, retirement_year, woman): return True
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    startIndex = max(0, 1950-index_year)
    
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    for i in range(startIndex, len(adjusted_income_stream)):
        if adjusted_income_stream[i]>=200:
            coverage_quarters+=4
        elif adjusted_income_stream[i] >=150:
            coverage_quarters +=3
        elif adjusted_income_stream[i] >=100:
            coverage_quarters +=2
        elif adjusted_income_stream[i] >=100:
            coverage_quarters +=1
    reference_year=max(1951,birth_year+21) #odd nuance of the legislation
    if coverage_quarters>40:
        return True
    elif (2*(coverage_quarters/4)>=(birth_year+65)-reference_year) and (coverage_quarters>=6):
        return True
    else:
        return False

def qcurrent1952(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
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

#benefit rules, these were updated by the 1952 legislation. The primary updates can be found on page 2 of the pdf, and the table update can be found on page 1 of the pdf
def bb1952(adjusted_income_stream:list, original_income_stream:list, avg_monthly_wage:float, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function determines whether an individual is considered fully-insured as of the 1952 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1952 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    #initialize variables
    pia=0
    pib=0 
    #avg_monthly_wage=a1952(adjusted_income_stream, index_year, birth_year,retirement_year, reference_year, woman)    #print("the average monthly wage: ", avg_monthly_wage)
    #if (birth_year+65<1950): #this checks if they are old enough to have a pib; someone who did have a pib would receive a new updated pia based on these charts below, if they do they go through the formulas differently. This is what the tables primarily deal with.
    pib=b1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year,reference_year, woman)
    #These initialize the tables used in the pia formula in the cases of turning 22 before 1950
    
    pib_list=[10, 11, 12, 13, 14, 15, 16 ,17, 18, 19, 20, 21,
              22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 
              35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]
    
    pia_list=[25.00, 27.00, 29.00, 31.00, 33.00, 35.00, 36.70, 38.20, 39.50, 40.70, 42.00, 43.50, 45.30, 
              47.50, 50.10, 52.40, 54.40, 56.30, 58.00, 59.40, 60.80, 62.00, 63.30, 64.40, 65.50, 
              66.60, 67.80, 68.90, 70.00, 71.00, 72.00, 73.10, 74.10, 75.10, 76.10, 77.10, 77.10,]
    
    average_monthly_wage_list=[45.00, 49.00, 53.00, 56.00, 60.00, 64.00, 67.00, 69.00, 72.00, 74.00, 76.00, 79.00, 82.00, 86.00, 
                               91.00, 95.00, 99.00, 109.00, 109.00, 120.00, 129.00, 139.00, 147.00, 155.00, 163.00, 170.00, 
                               177.00, 185.00, 193.00, 200.00, 207.00, 213.00, 221.00, 227.00, 234.00, 241.00, 250.00, 250.00]

    
    if ((q1952(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year,woman)==True) and (birth_year+22>=1951)):
        if avg_monthly_wage>=48:
            pia=(.55*min(avg_monthly_wage,100))+max((.15*min(avg_monthly_wage-100,200)),0)
        elif avg_monthly_wage<48 and avg_monthly_wage>=35:
            pia=26
        elif avg_monthly_wage<35:
            pia=25
            
    elif((q1952(adjusted_income_stream, original_income_stream, index_year, birth_year,retirement_year, woman)==True) and (birth_year+22<1951)):
        if avg_monthly_wage>=46:
            pia_A=(.55*min(avg_monthly_wage,100))+max((.15*min(avg_monthly_wage-100,200)),0)
        else:
            pia_A=25
            #checking what they would get if their pia's were simply updated from pib
        pia_B=0
        for i in range(2, len(pib_list)):
            if pib >= pib_list[i-1] and pib <= pib_list[i]:
                pia_B = pia_list[i-1] + (pia_list[i] - pia_list[i-1])*(pib - pib_list[i-1])
        pia=max(pia_A, pia_B)
        
    else:
        #checking what they would get if their pia's were simply updated from pib
        pia=0
        for i in range(2, len(pib_list)):
            if pib >= pib_list[i-1] and pib <= pib_list[i]:
                pia_B = pia_list[i-1] + (pia_list[i] - pia_list[i-1])*(pib - pib_list[i-1])
    
    return pia


# In[7]:


#output functions are in this cell: bYEAR returns a nominal monthly benefit (int), and tYEAR returns a list of nominal contributions
def b1952(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1952 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """ 
    monthly_benefits=0
    adjusted_income_stream=i1952(income_stream, index_year, retirement_year)



    if retirement_year <= 1950: avg_monthly_wage = a1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1952 : avg_monthly_wage = a1950(i1950(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    else: avg_monthly_wage = a1952(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, reference_year, woman, income_stream)
    #print("avg: ", avg_monthly_wage)
    #monthly_benefits=bb1952(adjusted_income_stream,avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)

    retirement_age=retirement_year-birth_year
    if q1952(adjusted_income_stream, original_income_stream,index_year, birth_year, retirement_year,woman):
        monthly_benefits=bb1952(adjusted_income_stream, original_income_stream, avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)
    else: monthly_benefits = 0

    return round(monthly_benefits,1)


#tax rules, same as 1950 legislation, see page 48 of the pdf
def t1952(income_stream:list, index_year:int):
    """This function outputs a list of nominal contributions an indvidual would have paid in social security tax under the 1952 legislation.
        The function inputs are (income_stream:list, index_year:int)
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """    
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    capped_income_stream=i1952(income_stream, index_year, index_year + len(income_stream))
    
    for i in range(len(capped_income_stream)): 
        if (i+index_year) <= 1949: #actual tax rates
             employee_tax_rate= 0.01
             employer_tax_rate= 0.01
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1953 and (i+index_year)>=1950: #proposed tax rates onwards
             employee_tax_rate= 0.015
             employer_tax_rate= 0.015
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1959 & (i+index_year) >=1954:
             employee_tax_rate= 0.02
             employer_tax_rate= 0.02
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1964 & (i+index_year) >=1960:
             employee_tax_rate= 0.025
             employer_tax_rate= 0.025
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (i+index_year) >=1965 and (i+index_year) <=1969:
             employee_tax_rate= 0.03
             employer_tax_rate= 0.03
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (i+index_year) >=1970: 
             employee_tax_rate= 0.03
             employer_tax_rate= 0.03
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
            
    return nominal_contributions


def death1952(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    '''
    if (q1952(income_stream, index_year, birth_year, retirement_year, woman)): 
        monthlyBenefits = b1952(income_stream, index_year, birth_year, retirement_year)
        return 3 * monthlyBenefits
    else:
        return 0

def spouse1952(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    if q1952(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_woman):
        spouse_benefit = b1952(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    
    primary_adjusted_income_stream=i1952(income_stream, index_year, retirement_year)
    
    primary_avg_monthly_wage = a1952(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    #print("problem! 2")
    primary_PIA = bb1952(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)

    #print(primary_PIA)

    #print("problem!")

    spouse_benefit_guarantee = 0.5*primary_PIA 

    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    return spousal_benefit

def widow1952(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if widow_retirement_year >= widow_birth_year + 65 and q1952(income_stream,index_year,birth_year,retirement_year, woman):
        if q1952(widow_income_stream,widow_index_year, widow_birth_year, widow_retirement_year, widow_woman):
            widowMonthlyBenefit = b1952(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_reference_year, widow_woman)
        else:  widowMonthlyBenefit = 0
        primary_adjusted_income_stream=i1952(income_stream, index_year, retirement_year)
        primary_avg_monthly_wage = a1952(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    
        primaryPIA = bb1952(income_stream,primary_avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)
        widow_benefit_guarantee = 0.75*primaryPIA 

        widow_benefit = 0
        if widowMonthlyBenefit < widow_benefit_guarantee:
            widow_benefit = widow_benefit_guarantee - widowMonthlyBenefit

        return round(widow_benefit,1)
    else:
        return 0
    
def MFB1952(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1952(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1952(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_avg_monthly_wage = math.floor(primary_avg_monthly_wage)
    maximumFamilyBenefit = max(45, min(168.75, .8* primary_avg_monthly_wage))
    return maximumFamilyBenefit


def children1952(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
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
    primary_adjusted_income_stream=i1952(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1952(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1952(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)


    return math.ceil(0.5* primary_PIA*10)/10