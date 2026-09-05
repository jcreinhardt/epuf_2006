#!/usr/bin/env python
# coding: utf-8

# In[3]:


#By Daniel Carrillo
#Benefit and tax rules for 1947

#THIS LEGISLATION IS IDENTICAL TO THE 1939 VERSION EXCEPT FOR TAX SCHEDULE CHANGES
#Accordingly, everything else is a simple copy and paste, and all leguislation referred to (apart from the tax rate changes) refers to the 1939 pdf

#As a general note, our model operates on a year by year flow of time. The actual Social Security Legislation works on a quarter by quarter flow of time
#This could cause certain distortions. For example, quarters of coverage will probably be overestimated, and periods of unemployment longer than a quarter will not show up in our model
#In our model, all the quarters are scaled to years. For example "the quotient obtained by dividing the total wages paid an individual before the quarter in which he died or became entitled to receive primary insurance benefits"
#Is read as "the quotient obtained by dividing the total wages paid an individual before the YEAR in which he died or became entitled to receive primary insurance benefits"
#As a note, there are no secondary benefits yet, and also maximum benefits have not been coded because those are related to secondary benefits
#last updated 1/29/25 by DC


# In[73]:


#iYEAR, aYEAR, qYEAR, and bbYEAR are all intermediate functions that are called within the main output functions in the next cell

#inputs
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


#this function puts the taxable maximums on the income stream; it can be found on page 14 of the pdf.
def i1947(income_stream:list, index_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1947 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy()
    for i in range(len(income_stream)):
        if i+index_year<1936:
            adjusted_income_stream[i]=0
        if income_stream[i]>3000 and i+index_year>=1936:
            adjusted_income_stream[i]=3000
    return adjusted_income_stream


#this function calculates average monthly wage (for the purposes of SSec legislation) from an income stream; it can be found on page 17 of the pdf page 17, section (f) 
#this assumes that people retire at 65, which was the full retirement year at this point
def a1947(income_stream:list, index_year:int, birth_year:int, retirement_year:int):
    """This function returns the average monthly wage (int) of an individual as determined by the 1947 legislation.
        This is more complicated than one might think, which is why it has its own seperate function.
        The inputs are (adjusted_income_stream:list,index_year:int, bith_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1947 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream   
        birth_year -- the year the individual is born.
    """
    total_wage=0
    count=0
    adjusted_income_stream=i1947(income_stream, index_year)
    for i in range(len(adjusted_income_stream)):
        if (i+index_year>1936) and not (i+index_year-22<birth_year and adjusted_income_stream[i]<200): #there's something else here, check
            count+=1
            total_wage+=adjusted_income_stream[i]
    if count==0:
        avg_monthly_wage=0
    else: 
        avg_monthly_wage=total_wage/(count*12)
    return avg_monthly_wage


#qualification rules, pdf page 17
#this is for people who are considered "fully insured individuals"; "currently insured individuals is a different category" see page 18 of the pdf
#also assuming that people retire at 65
#pay attention to what a "quarter of coverage" is defined as. This can be found on the top of page 18 of the pdf
#There's an odd rule here at the top of page 18 when wages hit 3k in a calendar year, as of 1/26/25, it is not relevant to our model
def q1947(adjusted_income_stream:list, index_year:int, birth_year:int): #this might not be completely correct/ might be off by half a year
    """This function determines whether an individual is considered fully-insured as of the 1947 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1947 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    for i in range(len(adjusted_income_stream)):
        if adjusted_income_stream[i]>200:
            coverage_quarters+=4
    reference_year=max(1936,birth_year+21) #odd nuance of the legislation
    if coverage_quarters>40:
        return True
    elif (2*(coverage_quarters/4)>=(birth_year+65)-reference_year) and (coverage_quarters>=6):
        return True
    else:
        return False


#benefit rules
def bb1947(avg_monthly_wage:int, adjusted_income_stream:list):
    """This function takes an average monthly wage and calculates the nominal monthly benefit (int) under the 1947 legislation.
        The inputs are (avg_monthly_wage:int, index_year:int, birth_year:int)
        avg_monthly_wage -- the average monthly wage a person received throughout their working history as determined by the 1947 legislation. a1947 will create this value for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """    
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



# In[75]:


#output functions are in this cell: bYEAR returns a nominal monthly benefit (int), and tYEAR returns a list of nominal contributions

#as a note, there are no secondary benefits yet, and also maximum benefits have not been coded because those are related to secondary benefits
def b1947(income_stream:list, index_year:int, birth_year:int, retirement_age:int):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1947 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """
    monthly_benefits=0
    retirement_year = index_year+len(income_stream)
    #retirement_age=retirement_year-birth_year

    if q1947(income_stream, index_year, birth_year)==True and retirement_age>=65:
        monthly_benefits=bb1947(income_stream,index_year,birth_year)
    
    return monthly_benefits


#tax rules, this is the only change to this legislation since the 1946 version. All it does is to continue to delay the schedule tax increase, keeping it at 1% for both employer and employee.
#https://www.dropbox.com/home/GZ%20SSec%20RA%20share%202023-present/project_carrillo/legislation/actual_legislation?preview=1947_amendments.pdf
def t1947(income_stream:list, index_year:int):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1947 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """     
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]
    adjusted_income_stream=i1947(income_stream, index_year)
    
    for i in range(len(adjusted_income_stream)):
        if (i+index_year) <1937:
             employee_tax_rate= 0.00
             employer_tax_rate= 0.00
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1949 and (i+index_year) >=1937:
             employee_tax_rate= 0.01
             employer_tax_rate= 0.01
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1951 and (i+index_year) >=1950:
             employee_tax_rate= 0.015
             employer_tax_rate= 0.015
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) >=1952:
             employee_tax_rate= 0.02
             employer_tax_rate= 0.02
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
            
    return nominal_contributions

def death1947(income_stream:list, index_year:int, birth_year:int, retirement_year:int, death_year:int, survivors:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    '''
    if (q1947(income_stream, index_year, birth_year) and not survivors): 
        monthlyBenefits = b1947(income_stream, index_year, birth_year, retirement_year)
        return 6 * monthlyBenefits
    else:
        return 0
    

def spouse1947(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
    """ 
    
    if spouse_woman == True and woman == False:
        spousal_benefit = 0
        spouseMonthlyBenefit = b1947(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year)
        primaryPIA = bb1947(income_stream, index_year, birth_year)

        spouse_benefit_guarantee = 0.5*primaryPIA 

        spousal_benefit = 0
        if spouseMonthlyBenefit < spouse_benefit_guarantee:
            spousal_benefit = spouse_benefit_guarantee - spouseMonthlyBenefit
            
        return spousal_benefit
    else:
        return 0

def widow1947(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if widow_woman == True and widow_retirement_year >= widow_birth_year + 65 and q1947(income_stream,index_year,birth_year):
        spousal_benefit = 0
        spouseMonthlyBenefit = b1947(widow_income_stream, widow_index_year, widow_birth_year)
        primaryPIA = bb1947(income_stream, index_year, birth_year)

        spouse_benefit_guarantee = 0.75*primaryPIA 

        spousal_benefit = 0
        if spouseMonthlyBenefit < spouse_benefit_guarantee:
            spousal_benefit = spouse_benefit_guarantee - spouseMonthlyBenefit

        return spousal_benefit
    else:
        return 0
    
def MFB1947(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1947(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1947(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primaryMonthlyBenefit = b1947(primary_adjusted_income_stream, index_year, birth_year, retirement_year, reference_year, woman)

    maximumFamilyBenefit = max(20, min(85, 2*primaryMonthlyBenefit, .8* primary_avg_monthly_wage))
    return maximumFamilyBenefit