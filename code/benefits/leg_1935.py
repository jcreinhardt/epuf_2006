#!/usr/bin/env python
# coding: utf-8

# In[6]:


#By Daniel Carrillo
#Benefit and tax rules for 1935
#I could probably be more specific and cite the sections of the legislative code

# In[1]:
#1935
#income stream modifer, found on page 6 of pdf, the income streams are not on a quarter system here!
def i1935(income_stream:list):
    """ This function takes in a list of income stream. All incomes abovable the taxable max is changed to the max."""
    adjusted_income_stream=income_stream
    for i in range(len(adjusted_income_stream)):
        if adjusted_income_stream[i]>3000:
            adjusted_income_stream[i]=3000
    return adjusted_income_stream
    
#usually an average monthly wage calculator, here it is a total wage calculator, rememmber to pass the adjusted income stream into here, not the original 
def a1935(adjusted_income_stream:list):
    """ This function sums the list of lifetime adjusted earning stream. """
    total_wage=0
    for i in range(len(adjusted_income_stream)):
        total_wage+=adjusted_income_stream[i]
    return total_wage
    
#tax rules, found on pdf page 17-18, remember to pass the adjusted income stram into this!
#https://www.ssa.gov/history/pdf/Downey%20PDFs/Social%20Security%20Act%20of%201935%20Vol%202.pdf#page=296
def t1935(adjusted_income_stream:list, index_year:int): ##this needs to be fixed
    """ This function takes the adjusted income list and the year assocaited with the first index. This will output the Nominal total tax contributions as a list."""
    # Tax rules
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_total_contributions=0
    for i in range(len(adjusted_income_stream)): 
        if (i+index_year)>= 1937 and (i+index_year)<= 1939:
            employee_tax_rate = .01
            employer_tax_rate = .01
            nominal_total_contributions+=adjusted_income_stream[i]*employee_tax_rate
        elif (i+index_year)>= 1940 and (i+index_year)<= 1942:
            employee_tax_rate = .015
            employer_tax_rate = .015
            nominal_total_contributions+=adjusted_income_stream[i]*employee_tax_rate
        elif (i+index_year)>= 1943 and (i+index_year)<= 1945:
            employee_tax_rate = .02
            employer_tax_rate = .02
            nominal_total_contributions+=adjusted_income_stream.loc[i,"income"]*employee_tax_rate
        elif (i+index_year) >= 1946 and (i+index_year)<= 1948:
            employee_tax_rate = .025
            employer_tax_rate = .025
            nominal_total_contributions+=adjusted_income_stream[i]*employee_tax_rate
        elif (i+index_year)> 1948:
            employee_tax_rate = .03
            employer_tax_rate = .03
            nominal_total_contributions+=adjusted_income_stream[i]*employee_tax_rate

    return nominal_total_contributions ##should change this to real? there will be a discounting factor here
    
# Benefit rules, found on page 4 of pdf
#https://www.ssa.gov/history/pdf/Downey%20PDFs/Social%20Security%20Act%20of%201935%20Vol%202.pdf#page=281
def b1935(total_wages: int):
    """ This function takes in total wages and calculates the benefits."""
    if total_wages <= 3_000:
        benefits = .005 * total_wages
    elif total_wages > 3_000 and total_wages < 45_000:
        benefits = (.005 * 3_000) + ((.01 / 12) * (total_wages - 3_000))
    elif total_wages >= 45_000:
        benefits = (.005 * 3_000) + ((.01 / 12) * (45_000 - 3_000)) + ((.01 / 24) * (total_wages - 45_000))
    
    if benefits > 85:
        benefits = 85

    return benefits

#payments to aged individuals not qualified for benefits, found on page 5 of pdf
def e1935 (total_wages: int):
    exception_payment=.035*total_wages
    return exception_payment
    
#how to find if qualified, on page 4
def q1935 (year_of_birth:int, year_of_retirement: int, total_wages:int):
    if year_of_retirement-year_of_birth>=65 and total_wages>=2000 and year_of_retirement>=1942:
        return True
    else:
        return 
    
#full model for this year, will need to figure out inputs. #assumes begin work at 25! #assumes covered employment! #also I need to conver this to real!
def y1935(year_of_birth: int, year_of_retirement:int, year_of_death:int, income_stream:list, index_year:int):
    
    adjusted_income_stream=i1935(income_stream)
    
    total_wage=a1935(adjusted_income_stream)
    
    nominal_total_contributions=t1935(adjusted_income_stream, index_year)
    
    if q1935(year_of_birth,year_of_retirement, total_wage)==True:
        monthly_benefits=b1935(total_wage)
    else:
        monthly_benefits=0
        unqualified_lump_sum=e1935(total_wage)

    if year_of_death<year_of_birth + 65:
        death_lump_sum=d1935(total_wages)
    else:
        lump_sum=0
        
    return monthly_benefits

def death1935(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    '''
    adjusted_income_stream=i1935(income_stream)
    #taxStream = t1935(adjusted_income_stream, index_year)
    totalCoveredWages = sum(adjusted_income_stream)
    monthlyBenefit = b1935(sum(totalCoveredWages))
    qualified = q1935(birth_year, retirement_year, sum(income_stream))

    if qualified:
        if death_year < birth_year + 65:
            return 0.035 * totalCoveredWages
        else:
            return max(0, 0.035* totalCoveredWages - 12 * monthlyBenefit * (retirement_year - death_year))
    else:
        return 0.035 * totalCoveredWages
    
def spouse1935(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
    """ 
    
    return 0 

def widow1939(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    return 0