#!/usr/bin/env python
# coding: utf-8

# In[37]:


#By Daniel Carrillo (DC)
#Coded tax and benefit rules for 1950

#As a general note, our model operates on a year by year flow of time. The actual Social Security Legislation works on a quarter by quarter flow of time
#This could cause certain distortions. For example, quarters of coverage will probably be overestimated, and periods of unemployment longer than a quarter will not show up in our model
#In our model, all the quarters are scaled to years. For example "the quotient obtained by dividing the total wages paid an individual before the quarter in which he died or became entitled to receive primary insurance benefits"
#Is read as "the quotient obtained by dividing the total wages paid an individual before the YEAR in which he died or became entitled to receive primary insurance benefits"

#As a note, there are no secondary benefits yet, and also maximum benefits have not been coded because those are related to secondary benefits
#THERE IS ALSO SIZEABLE WW2 SPECIAL BENEFITS in this legislation; it has not been coded yet

#last updated 3/25/25 by DC


# In[4]:


#iYEAR, aYEAR, qYEAR, and bbYEAR are all intermediate functions that are called within the main output functions in the next cell


#inputs
import numpy as np
import math
from leg_1939 import *

#this function puts the taxable maximums on the income stream; it can be found on page 17 of the pdf.
def i1950(income_stream:list,index_year:int, retirement_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1950 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy()
    for i in range(len(income_stream)):
        if i+index_year<=1936:
            adjusted_income_stream[i]=0
        if income_stream[i]>3600 and i+index_year>1950:
            adjusted_income_stream[i]=3600
        if income_stream[i]>3000 and i+index_year<1951 and i+index_year>1936:
            adjusted_income_stream[i]=3000
    return adjusted_income_stream


#average monthly wage calculator
#can be found on pdf page 30; this has the interesting dynamic of not counting any wages between 1936-1950
#also, the average monthly wage has two versions, one where the beginning year is 1950, one where it is the day before the quarter the worker turns 22
#the higher of these two versions becomes the "average monthly wage" for all other purposes

def a1950(adjusted_income_stream:list, original_income_stream, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function returns the average monthly wage (int) of an individual as determined by the 1950 legislation.
        This is more complicated than one might think, which is why it has its own seperate function.
        The inputs are (adjusted_income_stream:list,index_year:int, bith_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1950 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream   
        birth_year -- the year the individual is born.
    """
    # total_wage=0
    # for i in range(len(adjusted_income_stream)): 
    #     if (i+index_year)<end_year and (i+index_year)>=beginning_year:
    #         total_wage+=adjusted_income_stream[i]

    avg_monthly_wage_A=0
    avg_monthly_wage_B=0
    



#Case 1: The starting date is 1950
    beginning_year = 1951 #index_year #AV: On page 30 of the pdf it says the start data is 1951 or when they turn 22, but the earliest start dat is 1950
    end_year = birth_year+65  

    if end_year <= beginning_year: #If the individual turned 65 before 1951 but retired late, after 1951
        beginning_year = retirement_year - 1
    total_wage=0
    count=0

    # Calc the total wages between start and end date.
    startIndex = max(0, 1950-index_year)
    for i in range(startIndex, len(adjusted_income_stream)): 
        if (i+index_year)<end_year and (i+index_year)>=beginning_year:
            total_wage+=adjusted_income_stream[i]
            
    
    count = (end_year - beginning_year)
    yrBefore22andNotCovered = 0
    yr_22 = birth_year + 22

    if yr_22 > beginning_year:
        for i in range(beginning_year,yr_22): # Go through all years they are < 22 age
            if 0<=i-index_year and i-index_year <  len(adjusted_income_stream) and adjusted_income_stream[i-index_year]<200: # Check that it is a valid income index and they make less than 200. 
                yrBefore22andNotCovered += 1 # Add one to not covered

    count = count - yrBefore22andNotCovered
    #print(count)
    avg_monthly_wage_A=total_wage/(max(18,count*12))


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
        #print(count)
        avg_monthly_wage_B=total_wage/(max(18,count*12))
        
    #     beginning_year = birth_year+22
    #     end_year = index_year + len(adjusted_income_stream)
    #     total_wage=0
    #     count=0
    #     for i in range(len(adjusted_income_stream)):
    #         if (i+index_year)<end_year and (i+index_year)>=beginning_year:
    #             total_wage+=adjusted_income_stream[i]
    #             count+=1
    #     if count==0:
    #         avg_monthly_wage_B=0
    #     else:
    #         avg_monthly_wage_B=total_wage/(count*12)
    # else:
    #     avg_monthly_wage_B=0
        
    avg_monthly_wage=max(avg_monthly_wage_A, avg_monthly_wage_B)

    return math.floor(avg_monthly_wage)


#qualification rules, pdf page 29
#note the difference between fully-insured individuals and currently insured individuals in the legislation, this function only refers to fully-insured individuals
#only diffrence from 1939-1947 amendments is that the "base year" is now 1950 instead of 1939
def q1950(adjusted_income_stream:list, original_income_stream, index_year:int, birth_year:int, retirement_year:int, woman:bool): #this might not be completely correct/ might be off by half a year
    """This function determines whether an individual is considered fully-insured as of the 1950 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1950 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    if q1939(i1939(original_income_stream, index_year, retirement_year), index_year, birth_year, retirement_year, woman): return True
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    startIndex = max(0, 1950-index_year)
    for i in range(startIndex, len(adjusted_income_stream)):
        if adjusted_income_stream[i]>200:
            coverage_quarters+=4
    reference_year=max(1951,birth_year+21) #odd nuance of the legislation
    if coverage_quarters>40:
        return True
    elif (2*(coverage_quarters/4)>=(birth_year+65)-reference_year) and (coverage_quarters>=6):
        return True
    else:
        return False



def qcurrent1950(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
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

#benefit rules, pdf page 30
#these are quite difference from the previous legislation
#https://www.dropbox.com/home/GZ%20SSec%20RA%20share%202023-present/project_carrillo/legislation/actual_legislation?preview=1950_amendments.pdf
def bb1950(adjusted_income_stream:list, original_income_stream:list, avg_monthly_wage:float,index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function takes an average monthly wage and calculates the nominal monthly benefit (int) under the 1950 legislation.
        The inputs are (avg_monthly_wage:int, index_year:int, birth_year:int)
        avg_monthly_wage -- the average monthly wage a person received throughout their working history as determined by the 1950 legislation. a1950 will create this value for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    #initialize variables
    pia=0
    pib=0 
    # if birth_year + 65 <= 1962:
    #     avg_monthly_wage = a1939(adjusted_income_stream, index_year, birth_year, retirement_year, reference_year,woman)
    # else:
    #     avg_monthly_wage= avg_monthly_wage
    

    pib=b1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year,retirement_year, reference_year, woman)
    #These initialize the tables used in the pia formula in the cases of turning 22 before 1950
    pib_list=[10, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 
     23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 
     35.0, 36.0, 37.0, 38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0]
    
    pia_list=[20.0, 22.0, 24.0, 26.0, 28.0, 30.0, 31.7, 33.2, 34.5, 35.7, 37.0, 38.5, 
     40.2, 42.2, 44.5, 46.5, 48.3, 50.0, 51.5, 52.8, 54.0, 55.1, 56.2, 57.2, 
     58.2, 59.2, 60.2, 61.2, 62.2, 63.1, 64.0, 64.9, 65.8, 66.7, 67.6, 68.5, 68.5]
    average_monthly_wage_list=[40.0, 44.0, 48.0, 52.0, 56.0, 60.0, 63.4, 66.4, 69.0, 71.4, 74.0, 77.0, 
     80.4, 84.4, 89.0, 93.0, 96.6, 100.0, 110.0, 118.6, 126.6, 134.0, 141.3, 
     148.0, 154.6, 161.3, 168.0, 174.6, 181.3, 187.3, 195.0, 210.0, 220.0, 
     230.0, 240.0, 250.0, 250.0] #this is for calculating mfb, not anythinbg else


    #The following is the actual pia formula
    
    if ((q1950(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, woman)==True) and (birth_year+22>=1951)): #Check if the worker is fully-insured, as well as to place them in the proper formula
        if avg_monthly_wage>=50:
            pia=(.5*min(avg_monthly_wage,100))+max((.15*min(avg_monthly_wage-100,200)),0)
        elif avg_monthly_wage<31:
            pia=20
        elif avg_monthly_wage==31:
            pia=21
        elif avg_monthly_wage==32:
            pia=22
        elif avg_monthly_wage==33:
            pia=23
        elif avg_monthly_wage==34:
            pia=24
        elif avg_monthly_wage<50 and avg_monthly_wage>35:
            pia=25 
        else:
            pia=0
            
    elif ((q1950(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, woman)==True) and (birth_year+22<1951)): #Check if the worker is fully-insured, as well as to place them in the proper formula
        if avg_monthly_wage>50:
            #print("the going in is ", avg_monthly_wage)
            pia_A=(.5*min(avg_monthly_wage,100))+max((.15*min(avg_monthly_wage-100,200)),0)
            #print("PIA: ", pia_A)
        elif avg_monthly_wage<30:
            pia_A=20
        elif avg_monthly_wage==31:
            pia_A=21
        elif avg_monthly_wage==32:
            pia_A=22
        elif avg_monthly_wage==33:
            pia_A=23
        elif avg_monthly_wage==34:
            pia_A=24
        elif avg_monthly_wage<50 and avg_monthly_wage>35:
            pia_A=25
        else:
            pia_A=0

        #checking what they would get if their pia's were simply updated from pib
        pia_B=0
        for i in range(2, len(pib_list)):
            if pib >= pib_list[i-1] and pib <= pib_list[i]:
                pia_B = pia_list[i-1] + (pia_list[i] - pia_list[i-1])*(pib - pib_list[i-1])            
        pia=max(pia_A, pia_B)

    else:
        #checking what they would get if their pia's were simply updated from pib
        pia_B=0
        for i in range(2, len(pib_list)):
            if pib >= pib_list[i-1] and pib <= pib_list[i]:
                pia_B = pia_list[i-1] + (pia_list[i] - pia_list[i-1])*(pib - pib_list[i-1])            
        pia=max(pia_A, pia_B)
    return pia


# In[5]:


#output functions are in this cell: bYEAR returns a nominal monthly benefit (int), and tYEAR returns a list of nominal contributions

#total 
def b1950(income_stream:list, original_income_stream:list,  index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """ 
    monthly_benefits=0
    #If the person became eligible for benefits (in this case, turned 65, before 1952, their benefits would be computed in the old way.
    
    adjusted_income_stream=i1950(income_stream, index_year, retirement_year)

    retirement_age=retirement_year-birth_year
    if retirement_age>=65:
        avg_monthly_wage = a1950(adjusted_income_stream, original_income_stream, index_year, retirement_year, birth_year, reference_year, woman)
        monthly_benefits=bb1950(adjusted_income_stream, original_income_stream,avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)
    else: monthly_benefits = 0
    return math.trunc(10* monthly_benefits)/ 10 #Drop cents

#tax rules, found on page 48 of the pdf
def t1950(income_stream:list, index_year:int):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """ 
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    adjusted_income_stream=i1950(income_stream, index_year) #to apply the taxable maximums to the benefit stream
    
    for i in range(len(adjusted_income_stream)): 
        if (i+index_year) <1937:
             employee_tax_rate= 0.00
             employer_tax_rate= 0.00
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)            
        if (i+index_year) <= 1949 and (i+index_year)>=1937: #actual tax rates
             employee_tax_rate= 0.01
             employer_tax_rate= 0.01
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1953 and (i+index_year)>=1950: #proposed tax rates onwards
             employee_tax_rate= 0.015
             employer_tax_rate= 0.015
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1959 & (i+index_year) >=1954:
             employee_tax_rate= 0.02
             employer_tax_rate= 0.02
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1964 & (i+index_year) >=1960:
             employee_tax_rate= 0.025
             employer_tax_rate= 0.025
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) >=1965 and (i+index_year) <=1969:
             employee_tax_rate= 0.03
             employer_tax_rate= 0.03
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) >=1970: 
             employee_tax_rate= 0.0325
             employer_tax_rate= 0.0325
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
            
    return nominal_contributions


def death1950(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    '''
    if (q1950(income_stream, index_year, birth_year, woman)): 
        monthlyBenefits = b1950(income_stream, index_year, birth_year, retirement_year)
        return 3 * monthlyBenefits
    else:
        return 0
    
def spouse1950(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    if q1950(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_woman):
        spouse_benefit = b1950(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    primary_adjusted_income_stream=i1950(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1950(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1950(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)

    spouse_benefit_guarantee = 0.5*primary_PIA 

    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    return spousal_benefit


def widow1950(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if widow_retirement_year >= widow_birth_year + 65 and q1950(income_stream,index_year,birth_year, woman):
        widow_benefit = 0
        widowMonthlyBenefit = b1950(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_woman)
        primaryPIA = bb1950(income_stream, index_year, retirement_year,birth_year)

        spouse_benefit_guarantee = 0.75*primaryPIA 

        spousal_benefit = 0
        if widowMonthlyBenefit < spouse_benefit_guarantee:
            spousal_benefit = spouse_benefit_guarantee - widowMonthlyBenefit

        return  math.trunc(10* widow_benefit)/ 10
    else:
        return 0
    
def MFB1950(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1950(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1950(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)

    maximumFamilyBenefit = max(40, max(150, .8* primary_avg_monthly_wage))
    return maximumFamilyBenefit

def children1950(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
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
    primary_adjusted_income_stream=i1950(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1950(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1950(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)


    return math.ceil(10*0.5* primary_PIA)/10