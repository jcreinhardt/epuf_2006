#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# from amendments_1935_model import *
# from amendments_1939_model import *
# from amendments_1943_model import *
# from amendments_1944_model import *
# from amendments_1945_model import *
# from amendments_1946_model import *
# from amendments_1947_model import *
# from amendments_1950_model import *
# from amendments_1952_model import *
# from amendments_1954_model import *
# from amendments_1956_model import *
# from amendments_1958_model import *
# from amendments_1960_model import *
# from amendments_1961_model import *
# from amendments_1965_model import *
# from amendments_1966_model import *
# from amendments_1967_model import *
# from amendments_1969_model import *
# from amendments_1971_model import *
# from amendments_1972_model import *
# from amendments_1973_model import *
# from amendments_1977_model import *

#1977 currently returns in 2024 dollars!

from leg_1973 import *

# In[ ]:

#cpi-w, first year is 1970 and last year is 2025
cpi = [39.0, 40.7, 42.1, 44.7, 49.6, 54.1, 57.2, 60.9, 65.6, 73.1, 82.9,
             91.4, 96.9, 99.8, 103.3, 106.9, 108.6, 112.5, 117.0, 122.6, 129.0, 
             134.3, 138.2, 142.1, 145.6, 149.8, 154.1, 157.6, 159.7, 163.2, 168.9, 
             173.5, 175.9, 179.8, 184.5, 191.0, 197.1, 202.8, 211.1, 209.6, 214.0, 
             221.6, 226.2, 229.3, 232.8, 231.8, 234.1, 239.1, 245.1, 249.2, 252.2, 
             265.5, 288.0, 299.0, 307.6]



#aime calculator
avg_wage_idx = {
    1951: 2799.16,
    1952: 2973.32,
    1953: 3139.44,
    1954: 3155.64,
    1955: 3301.44,
    1956: 3532.36,
    1957: 3641.72,
    1958: 3673.80,
    1959: 3855.80,
    1960: 4007.12,
    1961: 4086.76,
    1962: 4291.40,
    1963: 4396.64,
    1964: 4576.32,
    1965: 4658.72,
    1966: 4938.36,
    1967: 5213.44,
    1968: 5571.76,
    1969: 5893.76,
    1970: 6186.24,
    1971: 6497.08,
    1972: 7133.80,
    1973: 7580.16,
    1974: 8030.76,
    1975: 8630.92,
    1976: 9226.48,
    1977: 9779.44,
    1978: 10556.03,
    1979: 11479.46,
    1980: 12513.46,
    1981: 13773.10,
    1982: 14531.34,
    1983: 15239.24,
    1984: 16135.07,
    1985: 16822.51,
    1986: 17321.82,
    1987: 18426.51,
    1988: 19334.04,
    1989: 20099.55,
    1990: 21027.98,
    1991: 21811.60,
    1992: 22935.42,
    1993: 23132.67,
    1994: 23753.53,
    1995: 24705.66,
    1996: 25913.90,
    1997: 27426.00,
    1998: 28861.44,
    1999: 30469.84,
    2000: 32154.82,
    2001: 32921.92,
    2002: 33252.09,
    2003: 34064.95,
    2004: 35648.55,
    2005: 36952.94,
    2006: 38651.41,
    2007: 40405.48,
    2008: 41334.97,
    2009: 40711.61,
    2010: 41673.83,
    2011: 42979.61,
    2012: 44321.67,
    2013: 44888.16,
    2014: 46481.52,
    2015: 48098.63,
    2016: 48642.15,
    2017: 50321.89,
    2018: 52145.80,
    2019: 54099.99,
    2020: 55628.60,
    2021: 60575.07,
    2022: 63795.13,
    2023: 66621.80
}

def dollarConversion(dollar: int, begin_yr: int, end_yr: int):
    return round(dollar * (avg_wage_idx[end_yr]/avg_wage_idx[begin_yr]),2)
    


# In[ ]:


#extra years are added in pdf page 5 of 1977, but the indexing legislation is found on pdf page 12 of 1972
def i1977(income_stream:list, index_year:int, retirement_year:int):
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
        if income_stream[i]>6600 and (index_year+i)<=1967 and (index_year+i)>=1966:
            adjusted_income_stream[i]=6600 
        if income_stream[i]>7800 and (index_year+i)<=1971 and (index_year+i)>=1968:
            adjusted_income_stream[i]=7800
        if income_stream[i]>9000 and (index_year+i)>=1972:
            adjusted_income_stream[i]=9000 
        if income_stream[i]>10800 and (index_year+i)==1973:
            adjusted_income_stream[i]=10800
        if income_stream[i]>13200 and (index_year+i)>=1974:
            adjusted_income_stream[i]=13200
        if income_stream[i]>14100 and (index_year+i)==1975:
            adjusted_income_stream[i]=14100
        if income_stream[i]>15300 and (index_year+i)==1976:
            adjusted_income_stream[i]=15300
        if income_stream[i]>16500 and (index_year+i)==1977:
            adjusted_income_stream[i]=16500
        if income_stream[i]>17700 and (index_year+i)==1978:
            adjusted_income_stream[i]=17700
        if income_stream[i]>22900 and (index_year+i)==1979:
            adjusted_income_stream[i]=22900
        if income_stream[i]>25900 and (index_year+i)==1980:
            adjusted_income_stream[i]=25900
        if income_stream[i]>29700 and (index_year+i)==1981:
            adjusted_income_stream[i]=29700

        if (index_year+i)>=1982: #this is the indexing of the contribution base found on page 13 of 1972         
            taxable_maximum=29700
            last_base_year=1981 #check this
            for i in range(1982, index_year+len(income_stream)): 
                if cpi[i-1970]>1.03*cpi[last_base_year-1970]:
                    cpi_increase=cpi[i-1970]/cpi[last_base_year-1970]
                    taxable_maximum=taxable_maximum*cpi_increase
                    last_base_year=i
            if income_stream[i-index_year]>taxable_maximum: #this is actually still missing a rounding adjustment from page 13 of pdf
                adjusted_income_stream[i-index_year]=taxable_maximum

    return adjusted_income_stream

# #page 9 and 10 of pdf
# def a1977(adjusted_income_stream:list, index_year:int,):

#     beginning_year = index_year
#     end_year = index_year + len(adjusted_income_stream)
    
#     for i in range(len(adjusted_income_stream)):
#         year=end_year
#         wage_proportion=adjusted_income_stream[i]/wage_data.loc[index_year+i-1929,"awi"]
#         adjusted_income_stream[i]=wage_proportion*wage_data.loc[end_year-1929,"awi"]
#     total_wage=0
#     count=0
#     for i in range(len(adjusted_income_stream)): 
#         if (index_year+i)<end_year and (index_year+i)>=beginning_year:
#             total_wage+=(adjusted_income_stream[i]/awi.loc[i,"wage"])
#             count+=1
#     if count==0:
#         avg_index_monthly_wage=0
#     else:
#         avg_index_monthly_wage=total_wage/(count*12)
#     return avg_index_monthly_wage

# def calcAIME(earningHist, retire_yr, first_work_yr): #pdf page 9-10
#     """ - earningHist is a list earnings history for years afters 1950.
#         - retire_yr is the year at which they retire. 
#         - first_work_yr is the first year of work index 0 of earningHist"""
    
#     final_idx_yr = retire_yr - 2 # if a person retires 2024 we index to 2022 according to rules
    
#     for yr_idx in range(0, len(earningHist)):
#         #index the wages to the year that they retire
#         earningHist[yr_idx] = round(earningHist[yr_idx] * (avg_wage_idx[final_idx_yr]/avg_wage_idx[yr_idx]),2)

#     #Drop the lowest 5 years
#     num_yr_worked = len(earningHist)
    
#     sorted_inc = sorted(earningHist)  # Sort the list of incomes
#     largest_inc = [x for x in earningHist if x not in sorted_inc[:5]] #drop the lowest 5 incomes
    
#     if len(largest_inc) < 2: # the income cannot be smaller than 2 thus we get the larest 2 otherwise
#         largest_inc = sorted(earningHist, reverse=True)[:2]


# #AV: WE NEED TO CHECK HOW THE INCOME STREAM IS ADJUESTED PDF PAGE 10-11 PARAGRAPH 3.
#     #check how many years they worked
#     non_zero_count = sum(1 for value in largest_inc if value != 0)

#     # person must have worked at least 2 years
#     if non_zero_count < 2:
#         return 0
        
#     return round(sum(largest_inc)/(len(largest_inc)*12),2)



def a1977(adjusted_income_stream: list, index_year: int, birth_year: int, current_year: int) -> float:
    """ 
    adjusted_income_stream: List of income adjusted for tax max
    index_year: The year corresponding to index 0 in the list of incomes
    birth_year: The person's birth year
    current_year: The year to which we must index inflation
    """
    
    # Define the starting year for elapsed years calculation
    start_year = max(1950, birth_year + 22, index_year)

    # Define the end year based on when the person turns 65
    end_year = birth_year + 65  

    # Calculate elapsed years
    elapsed_years = max(0, end_year - start_year)

    # Compute benefit computation years (elapsed years - 5, but at least 2)
    benefit_computation_years = max(2, elapsed_years - 5)
    
    # Define the year that we are indexing inflation to
    final_inf_idx_yr = current_year - 2  # Social Security rules index wages to two years before retirement

    # Inflate all yearly wages
    for yr_idx in range(len(adjusted_income_stream)):
        actual_year = index_year + yr_idx  # Map index to actual year
        if (actual_year in avg_wage_idx) and (final_inf_idx_yr in avg_wage_idx):
            adjusted_income_stream[yr_idx] = round(
                adjusted_income_stream[yr_idx] * (avg_wage_idx[final_inf_idx_yr] / avg_wage_idx[actual_year]), 2
            )
    
    # Select the highest benefit computation years
    top_inc_years = sorted(adjusted_income_stream, reverse=True)[:benefit_computation_years]
    
    # Calculate AIME: (Sum of top earnings) / (Months in benefit computation years)
    aime = sum(top_inc_years) / (benefit_computation_years * 12)
    
    return aime



# page 1514 or pdf page 7, not correct
def bb1977(avg_monthly_wage:int, income_stream:list, index_year:int, birth_year:int):
    
    retirement_year = index_year + len(income_stream)
    current_year=retirement_year

    # Remove zeros in-place
    income_stream = [value for value in income_stream if value != 0]
    # Get the length = year of coverage
    years_of_coverage = len(income_stream)    

    #the bend points are adjusted according to pdf page 7 of 1977
    bend_point_2=1085
    bend_point_1=180
    base_year=1979

    #Dollar conversion is already here to inflate the bend points
    
    # if (retirement_year)>1979: #this is the indexing of the contribution base found on page 13 of 1972         
    #     for i in range(1980, retirement_year): 
    #         if cpi.loc[i-1974,"avg"]>1.03*cpi.loc[i-last_base_year,"avg"]:
    #             cpi_increase=cpi.loc[i-1974,"avg"]/cpi.loc[i-last_base_year,"avg"]
    #             bend_point_2=bend_point_2*cpi_increase
    #             bend_point_1=bend_point_1*cpi_increase
    #             last_base_year=i
    if index_year+len(income_stream)<1979:
        # pia=b1973(income_stream, index_year, index_year-21) #this needs to be updated to 1973, there was a problem here with the code, currently this is being commented out as of 2/28/25 so we can make the average worker hypotheticals
        pia=0
    else:
        if avg_monthly_wage >= bend_point_2:
            pia = dollarConversion(bend_point_1, 1977, current_year) * 0.9 + dollarConversion((bend_point_2-bend_point_1), 1977, current_year) * 0.32 + 0.15 * dollarConversion((avg_monthly_wage - bend_point_2), 1977, current_year)
        if avg_monthly_wage < bend_point_2 and avg_monthly_wage >= bend_point_1:
            pia = dollarConversion(bend_point_1, 1977, current_year) * 0.9 + dollarConversion((avg_monthly_wage - bend_point_1), 1977, current_year) * 0.32
        if avg_monthly_wage <= bend_point_1:
            pia = dollarConversion(avg_monthly_wage, 1977, current_year) * 0.9 


    #early retirement penalty I still haven't added the work penalty for early retirement
    nra=65
    if (retirement_year-birth_year)<nra:
        early_deduction=12*(5/9 * .01)*(nra-(retirement_year-birth_year))
        pia=(1-early_deduction)*pia


    return pia


# In[ ]:


def b1977(income_stream:list, index_year:int, birth_year:int):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """ 
    monthly_benefits=0
    adjusted_income_stream=i1977(income_stream, index_year)
    nominal_total_contributions=t1977(adjusted_income_stream, index_year)
    avg_monthly_wage=a1977(adjusted_income_stream, index_year, birth_year, index_year+len(income_stream))

    monthly_benefits=bb1977(avg_monthly_wage, income_stream, index_year, birth_year)
    
    

    #indexing to 2023 dollars
    monthly_benefits=(monthly_benefits/(cpi[index_year+len(income_stream)-1970]))*cpi[54]
    return monthly_benefits
    
# pdf page 2-3 of 1977 amendments. Note that they report full OASDI taxes, not just OASI, so DI must be subtracted from them.
#note that disability insurance taxes is now active, these can be found on page 5 of 1977 pdf
def t1977(income_stream:list, index_year:int):
    
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    adjusted_income_stream=i1977(income_stream, index_year) #to apply the taxable maximums to the benefit stream
    
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
             employee_tax_rate= 0.02
             employer_tax_rate= 0.02
             disability_tax=.005
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) == 1959 :
             employee_tax_rate= 0.0225
             employer_tax_rate= 0.0225
             disability_tax=.005
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <=1961 and (index_year+i) >=1960:
             employee_tax_rate= 0.0275
             employer_tax_rate= 0.0275
             disability_tax=.005
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <=1962 and (index_year+i) >=1962: 
             employee_tax_rate= 0.02875
             employer_tax_rate= 0.02875
             disability_tax=.005
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <=1965 and (index_year+i) >=1963: 
             employee_tax_rate= 0.03375
             employer_tax_rate= 0.03375
             disability_tax=.005
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) ==1966: 
             employee_tax_rate= 0.035
             employer_tax_rate= 0.035
             disability_tax=.007
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1967 and (index_year+i) <=1967: 
             employee_tax_rate= 0.0355
             employer_tax_rate= 0.0355
             disability_tax=.007
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1968 and (index_year+i) <=1968: 
             employee_tax_rate= 0.03325
             employer_tax_rate= 0.03325
             disability_tax=.0095
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) ==1969: 
             employee_tax_rate= 0.0375
             employer_tax_rate= 0.0375
             disability_tax=.0095
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) ==1970: 
             employee_tax_rate= 0.0365
             employer_tax_rate= 0.0365
             disability_tax=.0110
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1971 and (index_year+i) <=1972: 
             employee_tax_rate= 0.0405
             employer_tax_rate= 0.0405
             disability_tax=.0110
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) == 1973: 
             employee_tax_rate= 0.043
             employer_tax_rate= 0.043
             disability_tax=.0110
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1974 and (index_year+i) <=1977: 
             employee_tax_rate= 0.04375
             employer_tax_rate= 0.04375
             disability_tax=.0115
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) ==1978: 
             employee_tax_rate= 0.04275
             employer_tax_rate= 0.04275
             disability_tax=.0155
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1979 and (index_year+i) <=1980: 
             employee_tax_rate= 0.0433
             employer_tax_rate= 0.0433
             disability_tax=.015
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) ==1981:
             employee_tax_rate= 0.04525
             employer_tax_rate= 0.04525
             disability_tax=.0165
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1982 and (index_year+i)<=1984:
             employee_tax_rate= 0.04575
             employer_tax_rate= 0.04575
             disability_tax=.0165
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1985 and (index_year+i)<=1989:
             employee_tax_rate= 0.0475
             employer_tax_rate= 0.0475
             disability_tax=.0190
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1990:
             employee_tax_rate= 0.051
             employer_tax_rate= 0.051
             disability_tax=.0220
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)

            
    return nominal_contributions


def death1977(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    woman: This is TRUE if the deceased was female.
    '''
    if (q1971(income_stream, index_year, birth_year)): 
        monthlyBenefits = b1977(income_stream, index_year, birth_year, retirement_year, woman)
        return max(3 * monthlyBenefits, 255)
    else:
        return 0

def spouse1977(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    if q1977(spouse_income_stream, spouse_index_year, spouse_birth_year):
        spouse_benefit = b1977(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    primary_adjusted_income_stream=i1977(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1977(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1977(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)
    
    deduction = 1

    if spouse_birth_year + 65 > spouse_retirement_year:
        deduction = deduction - (25/36) * 0.01 * 12 *(spouse_birth_year+65 - spouse_retirement_year)

    spouse_benefit_guarantee = 0.5*primary_PIA *deduction
    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    return spousal_benefit


def widow1977(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if (retirement_year >= widow_birth_year +60) and q1973(income_stream,index_year,birth_year):
        spousal_benefit = 0
        spouseMonthlyBenefit = b1977(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_woman)
        primaryPIA = bb1977(income_stream, index_year, birth_year,retirement_year, woman)
        primaryMonthlyBenefit = b1977(income_stream, index_year, birth_year, retirement_year, reference_year, woman)
        

        deduction = 1
        if (retirement_year <= widow_birth_year + 65):
            months = 12 * (widow_birth_year + 65 - retirement_year)

            deduction -= (5/9) * 0.01 * min(months, 36)

            if months > 36:
                extraMonths = 36 - months
                deduction -= (19/40) * 0.01 * extraMonths

        spouse_benefit_guarantee_pre_cap = primaryPIA  * deduction
        
        spouse_benefit_guarantee = spouse_benefit_guarantee_pre_cap
        #spouse_benefit_guarantee = min(spouse_benefit_guarantee_pre_cap, max(primaryMonthlyBenefit, primaryPIA * .825))

        spousal_benefit = 0
        if spouseMonthlyBenefit < spouse_benefit_guarantee:
            spousal_benefit = spouse_benefit_guarantee - spouseMonthlyBenefit

        return spousal_benefit
    else:
        return 0
    
def MFB1977(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1977(income_stream, index_year, retirement_year)
    avg_monthly_wage = a1977(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    pia = bb1977(primary_adjusted_income_stream, avg_monthly_wage, index_year,birth_year, retirement_year, reference_year, woman)


    bend_point_1=230
    bend_point_1_converted = dollarConversion(bend_point_1, 1977, retirement_year)
    bend_point_2=332
    bend_point_2_converted = dollarConversion(bend_point_2, 1977, retirement_year)
    bend_point_3 = 433
    bend_point_3_converted = dollarConversion(bend_point_3, 1977, retirement_year)
    base_year=1979

    if pia <= bend_point_1_converted:
        maximumFamilyBenefit = 1.5*pia
    elif pia <= bend_point_2_converted:
        maximumFamilyBenefit = 1.5 * bend_point_1_converted + (pia - bend_point_1_converted) * 2.72
    elif pia <= bend_point_3_converted:
        maximumFamilyBenefit = 1.5 * bend_point_1_converted + 2.72 * bend_point_2_converted + (pia - bend_point_2_converted) * 1.34
    else:
        maximumFamilyBenefit = 1.5 * bend_point_1_converted + 2.72 * bend_point_2_converted + 1.34 * bend_point_3_converted + (pia - bend_point_3_converted) * 1.75

    return math.ceil(maximumFamilyBenefit * 10) / 10