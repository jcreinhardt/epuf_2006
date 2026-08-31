#!/usr/bin/env python
# coding: utf-8

# In[30]:


#1973 coded legislation
#These data inputs might have to be adjusted and tested later
#THIS IS A PROBLEM LEGISLATION, 


#these currently use the intermediate assumptiosn found here https://www.ssa.gov/oact/TR/TRassum.html
avg_wage_index = {
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
    2023: 66621.80,
    2024: 66621.80,#anything 2024 and after is made using the assumptions found here https://www.ssa.gov/oact/TR/TRassum.html, this will need to be updated later
    2025: 69153.43,
    2026: 71642.95,
    2027: 74508.67,
    2028: 77712.54,
    2029: 81287.32,
    2030: 84863.96,
    2031: 88597.98,
    2032: 92496.29,
    2033: 96196.14,
}

#this is the cpi_w, where the yearly values are the average of the montly cpi-w of the third quarter, as according to social security
cpi={
    1974: 50.3,
    1975: 54.7,
    1976: 57.66666667,
    1977: 61.53333333,
    1978: 66.4,
    1979: 74.4,
    1980: 83.9,
    1981: 92.9,
    1982: 98.16666667,
    1983: 100.5333333,
    1984: 104.0666667,
    1985: 107.3333333,
    1986: 108.7,
    1987: 113.2666667,
    1988: 117.8,
    1989: 123.3333333,
    1990: 129.9,
    1991: 134.7,
    1992: 138.7666667,
    1993: 142.3666667,
    1994: 146.4,
    1995: 150.2333333,
    1996: 154.6333333,
    1997: 157.8666667,
    1998: 160.0,
    1999: 163.9333333,
    2000: 169.7,
    2001: 174.1333333,
    2002: 176.5666667,
    2003: 180.3,        
    2004: 185.1,
    2005: 192.7,
    2006: 199.0666667,
    2007: 203.596,
    2008: 215.4953333,
    2009: 211.0013333,
    2010: 214.1363333,
    2011: 223.2333333,
    2012: 226.936,
    2013: 230.3266667,
    2014: 234.2416667,
    2015: 233.2776667,
    2016: 235.0566667,
    2017: 239.668,
    2018: 246.352,
    2019: 250.1996667,
    2020: 253.4123333,
    2021: 268.4206667,
    2022: 291.9006667,
    2023: 301.2356667,
    2024: 308.729,
    2025: 315.521,
    2026: 323.094,
    2027: 330.848,
    2028: 338.788,
    2029: 346.919,
    2030: 355.245,
    2031: 363.771,
    2032: 372.502,
    2034: 381.442   
}


cola_adjustments = {
    1974:0,
    1975:0,
    1976: 0.08,
    1977: 0.064,
    1978: 0.059,
    1979: 0.065,
    1980: 0.099,
    1981: 0.143,
    1982: 0.112,
    1983: 0.074,
    1984: 0.035,
    1985: 0.035,
    1986: 0.031,
    1987: 0.013,
    1988: 0.042,
    1989: 0.04,
    1990: 0.047,
    1991: 0.054,
    1992: 0.037,
    1993: 0.03,
    1994: 0.026,
    1995: 0.028,
    1996: 0.026,
    1997: 0.029,
    1998: 0.021,
    1999: 0.013,
    2000: 0.024,
    2001: 0.035,
    2002: 0.026,
    2003: 0.014,
    2004: 0.021,
    2005: 0.027,
    2006: 0.041,
    2007: 0.033,
    2008: 0.023,
    2009: 0.058,
    2010: 0.0,
    2011: 0.0,
    2012: 0.036,
    2013: 0.017,
    2014: 0.015,
    2015: 0.017,
    2016: 0.0,
    2017: 0.003,
    2018: 0.02,
    2019: 0.028,
    2020: 0.016,
    2021: 0.013,
    2022: 0.059,
    2023: 0.087,
    2024: 0.032,
    2025: 0.025,
}

taxable_maximums = {
    1937: 3000, 1938: 3000, 1939: 3000, 1940: 3000, 1941: 3000, 1942: 3000, 1943: 3000, 1944: 3000,  
    1945: 3000, 1946: 3000, 1947: 3000, 1948: 3000, 1949: 3000, 1950: 3000, 1951: 3600, 1952: 3600,  
    1953: 3600, 1954: 3600, 1955: 4200, 1956: 4200, 1957: 4200, 1958: 4200, 1959: 4800, 1960: 4800,  
    1961: 4800, 1962: 4800, 1963: 4800, 1964: 4800, 1965: 4800, 1966: 6600, 1967: 6600, 1968:7800, 1969: 7800,  
    1970: 7800, 1971: 7800, 1972: 9000, 1973: 10800, 1974: 13200, 1975: 14100, 1976: 15300, 1977: 16500,  
    1978: 17700, 1979: 22900, 1980: 25900, 1981: 29700, 1982: 32400, 1983: 35700, 1984: 37800, 1985: 39600,  
    1986: 42000, 1987: 43800, 1988: 45000, 1989: 48000, 1990: 51300, 1991: 53400, 1992: 55500}

# In[29]:
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
from leg_1969 import *
from leg_1971 import *
from leg_1972 import *


def dollarConversion(dollar: int, begin_yr: int, end_yr: int):
    if end_yr in avg_wage_index.keys() and end_yr <= 2024:
        return round(dollar * (avg_wage_index[end_yr]/avg_wage_index[begin_yr]),2)
    else: 
        return round(dollar * (avg_wage_index[2024]/avg_wage_index[begin_yr]),2)

#For late retirements, late credits begin to accumulate the quarter in which an individual can retire. This function finds that quarter and year. 
def getQYYYQuarterQualified(adjusted_income_stream:list, index_year:int, birth_year:int, woman:bool):
    """Because our calculator indexes by years, the number of months of late retirement credits accrued is only in increments of 12. Some individuals began accruing late retirement credits in the previous year, but not by Feb. 2. This function ameliorates that issue.
        This function returns a tuple with the quarter and year where an individual has enough quarters to retire.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1950 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    nra = 65

    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    for i in range(len(adjusted_income_stream)):
        year = i + index_year
        temp = coverage_quarters
        if year < 1978:
            if adjusted_income_stream[i]>= 50 and adjusted_income_stream[i] < 100:
                coverage_quarters+=1
            elif adjusted_income_stream[i] >= 100 and adjusted_income_stream[i] < 150:
                coverage_quarters+= 2
            elif adjusted_income_stream[i] >= 150 and adjusted_income_stream[i] < 200:
                coverage_quarters+= 3
            elif adjusted_income_stream[i] >= 200:
                coverage_quarters+= 4
        else:
            amountPerQuarter = round(dollarConversion(250, 1976, i + index_year-2) / 10) * 10
            if adjusted_income_stream[i]>= amountPerQuarter and adjusted_income_stream[i] < 2 * amountPerQuarter:
                coverage_quarters+=1
            elif adjusted_income_stream[i] >= 2 * amountPerQuarter and adjusted_income_stream[i] < 3 * amountPerQuarter:
                coverage_quarters+= 2
            elif adjusted_income_stream[i] >= 3 * amountPerQuarter and adjusted_income_stream[i] < 4 * amountPerQuarter:
                coverage_quarters+= 3
            elif adjusted_income_stream[i] >= 4 * amountPerQuarter:
                coverage_quarters+= 4

    #print(coverage_quarters)
        #print("coverage quarters: ", coverage_quarters)
        test1 = 6
        test2 = 6
        beginning_year=max(1951,birth_year+21)
        #end_year = birth_year+62
        
        if woman==True:
            end_year=birth_year+62
        elif birth_year<1911:
            end_year= birth_year+65 #these can be found on page 13 of 1972 pdf
        elif birth_year==1911:
            end_year=birth_year+64
        elif birth_year==1912:
            end_year=birth_year+63
        else:
            end_year= birth_year+62
        
        drops=5

        reference_year=max(1951,birth_year+22)
        elasped_years=end_year-beginning_year
        #print("quarters needed: ", elasped_years)
        if (coverage_quarters)>=((4/4)*(elasped_years )) and (coverage_quarters>=6): #Temporarily
            test1 = elasped_years- temp
        if coverage_quarters>=40 and (index_year + i - birth_year >= nra):
            test2 = 40 - temp
            

        if test1 <6 or test2 <6:
            quarter = min(test1, test2)
            #print((quarter, index_year + i))
            return(quarter, index_year + i)
    return 0

#pdf page 7-8 in 1973
def i1973(income_stream:list, index_year:int, retirement_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1967 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy() #i could redo all of these as dictionaries?
    for i in range(len(income_stream)):
        if income_stream[i]>=0 and (index_year+i)<1951:
            adjusted_income_stream[i]=0
        if income_stream[i]>3600 and (index_year+i)<1955 and (index_year+i)>1950:
             adjusted_income_stream[i]=3600
        if income_stream[i]>4200 and (index_year+i)>=1955 and (index_year+i)<=1958:
             adjusted_income_stream[i]=4200
        if income_stream[i]>4800 and (index_year+i)<=1965 and (index_year+i)>=1959:
            adjusted_income_stream[i]=4800      
        if income_stream[i]>6600 and (index_year+i)>=1966 and (index_year+i)<=1967:
            adjusted_income_stream[i]=6600
        if income_stream[i]>7800 and (index_year+i)>=1968 and (index_year+i)<=1971:
            adjusted_income_stream[i]=7800
        if income_stream[i]>9000 and (index_year+i)==1972:
            adjusted_income_stream[i]=9000
        if income_stream[i]>10800 and (index_year+i)==1973:
            adjusted_income_stream[i]=10800
        if income_stream[i]>13200 and (index_year+i)==1974:
            adjusted_income_stream[i]=13200
        if income_stream[i]>14100 and (index_year+i)==1975:
            adjusted_income_stream[i]=14100
        if income_stream[i]>15300 and (index_year+i)==1976:
            adjusted_income_stream[i]=15300
        if income_stream[i]>16500 and (index_year+i)==1977:
            adjusted_income_stream[i]=16500

        #everything below is a simplication for sake of making a correct historical model. This is not valid if we're running counterfactuals on the 1973 version. This is rather complicated to just email me (DAC) for me to explain
        
        if income_stream[i]>17700 and (index_year+i)==1978:
            adjusted_income_stream[i]=17700
        if income_stream[i]>22900 and (index_year+i)==1979:
            adjusted_income_stream[i]=22900
        if income_stream[i]>25900 and (index_year+i)==1980:
            adjusted_income_stream[i]=25900
        if income_stream[i]>29700 and (index_year+i)==1981:
            adjusted_income_stream[i]=29700
        if income_stream[i]>32400 and (index_year+i)==1982:
            adjusted_income_stream[i]=32400
        if income_stream[i]>35700 and (index_year+i)==1983:
            adjusted_income_stream[i]=35700
        if income_stream[i]>37800 and (index_year+i)==1984:
            adjusted_income_stream[i]=37800
        if income_stream[i]>39600 and (index_year+i)==1985:
            adjusted_income_stream[i]=39600
        if income_stream[i]>42000 and (index_year+i)==1986:
            adjusted_income_stream[i]=42000
        if income_stream[i]>43800 and (index_year+i)==1987:
            adjusted_income_stream[i]=43800
        if income_stream[i]>45000 and (index_year+i)==1988:
            adjusted_income_stream[i]=45000
        if income_stream[i]>48000 and (index_year+i)==1989:
            adjusted_income_stream[i]=48000
        if income_stream[i]>51300 and (index_year+i)==1990:
            adjusted_income_stream[i]=51300
        if income_stream[i]>53400 and (index_year+i)==1991:
            adjusted_income_stream[i]=53400
        if income_stream[i]>55500 and (index_year+i)==1992:
            adjusted_income_stream[i]=55500
        if income_stream[i]>57600 and (index_year+i)==1993:
            adjusted_income_stream[i]=57600
        if income_stream[i]>60600 and (index_year+i)==1994:
            adjusted_income_stream[i]=60600
        if income_stream[i]>61200 and (index_year+i)==1995:
            adjusted_income_stream[i]=61200
        if income_stream[i]>62700 and (index_year+i)==1996:
            adjusted_income_stream[i]=62700
        if income_stream[i]>65400 and (index_year+i)==1997:
            adjusted_income_stream[i]=65400
        if income_stream[i]>68400 and (index_year+i)==1998:
            adjusted_income_stream[i]=68400
        if income_stream[i]>72600 and (index_year+i)==1999:
            adjusted_income_stream[i]=72600
        if income_stream[i]>76200 and (index_year+i)==2000:
            adjusted_income_stream[i]=76200
        if income_stream[i]>80400 and (index_year+i)==2001:
            adjusted_income_stream[i]=80400
        if income_stream[i]>84900 and (index_year+i)==2002:
            adjusted_income_stream[i]=84900
        if income_stream[i]>87000 and (index_year+i)==2003:
            adjusted_income_stream[i]=87000
        if income_stream[i]>87900 and (index_year+i)==2004:
            adjusted_income_stream[i]=87900
        if income_stream[i]>90000 and (index_year+i)==2005:
            adjusted_income_stream[i]=90000
        if income_stream[i]>94200 and (index_year+i)==2006:
            adjusted_income_stream[i]=94200
        
        last_base_year=2006
        if (index_year+i)>2006: #this is the indexing of the contribution base found on page 13 of 1972, I think this code is inefficient, it's looping too many times, we could move the generating part outside         
            taxable_maximum=94200
            for k in range(2006, index_year+i): 
                if cpi[k]>1.03*cpi[last_base_year]:
                    cpi_increase=cpi[k]/cpi[last_base_year]
                    taxable_maximum=taxable_maximum*cpi_increase
                    last_base_year=k
            if income_stream[i]>taxable_maximum: #this is actually still missing a rounding adjustment from page 13 of pdf
                adjusted_income_stream[i]=taxable_maximum

    return adjusted_income_stream


# @Daniel I don't think this changed since 1960 please double check me! I don't think it has either!
def a1973(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,woman:bool, death_year = 0):
    """This function returns the average monthly wage (int) of an individual as determined by the 1952 legislation.
        This is more complicated than one might think, which is why it has its own seperate function.
        The inputs are (adjusted_income_stream:list,index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, adjusted by the relevant legislation. i1952 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream   
        birth_year -- the year the individual is born.
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
    if death_year != 0:
        if woman==True:
            end_year=max(1961,min(death_year,birth_year+62))
        elif birth_year<1911:
            end_year=max(1961,min(death_year,birth_year+65)) #these can be found on page 13 of 1972 pdf
        elif birth_year==1911:
            end_year=max(1961,min(death_year,birth_year+64))
        elif birth_year==1912:
            end_year= max(1961,min(death_year,birth_year+63))
        else:
            end_year=max(1961,min(death_year,birth_year+62))
    else:
        if woman==True:
            end_year=max(1961,birth_year+62)
        elif birth_year<1911:
            end_year=max(1961,birth_year+65) #these can be found on page 13 of 1972 pdf
        elif birth_year==1911:
            end_year=max(1961,birth_year+64)
        elif birth_year==1912:
            end_year= max(1961,birth_year+63)
        else:
            end_year=max(1961,birth_year+62)
    drops=5

    elasped_years=end_year-beginning_year
    #print("elapsed: ", elasped_years)
    highest_years=elasped_years-drops
    #print("highest: ", highest_years)
    if highest_years<2:
        highest_years=2
    
    #print("adj: ", adjusted_income_stream)
    highest_indices = np.argsort(adjusted_income_stream)[-highest_years:] #python is right exclusive


    for i in range(len(adjusted_income_stream)): 
        
        if (i+index_year)>=beginning_year and (i in highest_indices):
            #print(i+index_year, " ", adjusted_income_stream[i])
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
    #print("count: ", count)
    #print("total: ", total_wage)
    avg_monthly_wage_A=total_wage/(max(24,count*12))

###################
    # Case 2: if you are born after 1951 you can use a different forum
    if birth_year+22>1950:#the reasoning here is that there is a distinction in the legislation between those who turn 22 before and after 1950.
        #Those who turn 22 after 1950 have the option to use either their age 22 income onward or 1950 income onwards to calculate the average montly wage, the method that maximizes average monthly wage is used automatically
        #Case 2: The starting date is year they turn 22
        beginning_year=1951
        if woman==True:
            end_year=birth_year+62
        elif birth_year<1911:
            end_year=birth_year+65 #these can be found on page 13 of 1972 pdf
        elif birth_year==1911:
            end_year=birth_year+64
        elif birth_year==1912:
            end_year=birth_year+63
        else:
            end_year=birth_year+62
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
    
    #print("average monthly wage: ", avg_monthly_wage)

    return math.floor(avg_monthly_wage)
    
#see 1961 pdf page 7, has not been updated since thens
def q1973(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int,  retirement_year:int, woman:bool, skip1939 = False ): #this might not be completely correct/ might be off by half a year
    """This function determines whether an individual is considered fully-insured as of the 1950 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, capped by the relevant legislation. i1950 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """

    if skip1939 == False and q1939(i1939(original_income_stream, index_year, retirement_year), index_year, birth_year, retirement_year, woman): 
        return True

    if (retirement_year < birth_year+62): return False
    beginning_year=max(1951,birth_year+21)
    #end_year = birth_year +62
    if woman==True:
        end_year=birth_year+62
    elif birth_year<1911:
        end_year= birth_year+65 #these can be found on page 13 of 1972 pdf
    elif birth_year==1911:
        end_year=birth_year+64
    elif birth_year==1912:
        end_year=birth_year+63
    else:
        end_year= birth_year+62
    drops=5
    

    elasped_years=end_year-beginning_year
    #print(elasped_years)
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    for i in range(len(adjusted_income_stream)):
        year = i + index_year
        if year < 1978:
            if adjusted_income_stream[i]>= 50 and adjusted_income_stream[i] < 100:
                coverage_quarters+=1
            elif adjusted_income_stream[i] >= 100 and adjusted_income_stream[i] < 150:
                coverage_quarters+= 2
            elif adjusted_income_stream[i] >= 150 and adjusted_income_stream[i] < 200:
                coverage_quarters+= 3
            elif adjusted_income_stream[i] >= 200:
                coverage_quarters+= 4
        else:
            amountPerQuarter = round(dollarConversion(250, 1976, i + index_year-2) / 10) * 10
            if adjusted_income_stream[i]>= amountPerQuarter and adjusted_income_stream[i] < 2 * amountPerQuarter:
                coverage_quarters+=1
            elif adjusted_income_stream[i] >= 2 * amountPerQuarter and adjusted_income_stream[i] < 3 * amountPerQuarter:
                coverage_quarters+= 2
            elif adjusted_income_stream[i] >= 3 * amountPerQuarter and adjusted_income_stream[i] < 4 * amountPerQuarter:
                coverage_quarters+= 3
            elif adjusted_income_stream[i] >= 4 * amountPerQuarter:
                coverage_quarters+= 4
    #print("cov:", coverage_quarters)
    #print(elasped_years)
    reference_year=max(1950,birth_year+21) #odd nuance of the legislation
    if coverage_quarters>40:
        return True
    elif ((coverage_quarters)>=((4/4)*elasped_years)) and (coverage_quarters>=6): #Temporarily
        return True
    else:
        return False


def qcurrent1973(adjusted_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
    """This function determines whether an individual is considered fully-insured as of the 1939 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int)
        income_stream -- a list of nominal incomes a person received in each year
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """

    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    if len(adjusted_income_stream) < 3 or death_year >= reference_year : return False
    for index, income in enumerate(adjusted_income_stream[-3:]):
        year = death_year - (3-index)
        if year < 1978:
            if income>= 50 and income < 100:
                coverage_quarters+=1
            elif income >= 100 and income < 150:
                coverage_quarters+= 2
            elif income >= 150 and income < 200:
                coverage_quarters+= 3
            elif income >= 200:
                coverage_quarters+= 4
        else:
            amountPerQuarter = round(dollarConversion(250, 1976, year-2) / 10) * 10
            if income>= amountPerQuarter and income < 2 * amountPerQuarter:
                coverage_quarters+=1
            elif income >= 2 * amountPerQuarter and income < 3 * amountPerQuarter:
                coverage_quarters+= 2
            elif income >= 3 * amountPerQuarter and income < 4 * amountPerQuarter:
                coverage_quarters+= 3
            elif income >= 4 * amountPerQuarter:
                coverage_quarters+= 4
    
    if coverage_quarters >= 6: return True
    else: return False


Thresholds = { # Sources: https://www.ssa.gov/oact/cola/yoc.html
    # 1951-1978: 25% of contribution/benefit base 
    1951: 900, 1952: 900, 1953: 900, 1954: 900, 1955: 1050, 1956: 1050, 
    1957: 1050, 1958: 1050, 1959: 1200, 1960: 1200, 1961: 1200, 1962: 1200,
    1963: 1200, 1964: 1200, 1965: 1200, 1966: 1650, 1967: 1650, 1968: 1650,
    1969: 1650, 1970: 1650, 1971: 1650, 1972: 2250, 1973: 2700, 1974: 3300,
    1975: 3525, 1976: 3825, 1977: 4125, 1978: 4425,
    
    # 1979-1990: 25% of old-law base
    1979: 4725, 1980: 5100, 1981: 5550, 1982: 6075, 1983: 6675, 1984: 7050,
    1985: 7425, 1986: 7875, 1987: 8175, 1988: 8400, 1989: 8925, 1990: 9525,
    
    # 1991+: 15% of old-law base
    1991: 5940, 1992: 6210, 1993: 6435, 1994: 6750, 1995: 6795, 1996: 6975,
    1997: 7290, 1998: 7605, 1999: 8055, 2000: 8505, 2001: 8955, 2002: 9450,
    2003: 9675, 2004: 9765, 2005: 10035, 2006: 10485, 2007: 10890, 2008: 11385,
    2009: 11880, 2010: 11880, 2011: 11880, 2012: 12285, 2013: 12645, 2014: 13050,
    2015: 13230, 2016: 13230, 2017: 14175, 2018: 14310, 2019: 14805, 2020: 15345,
    2021:15930, 2022: 16380, 2023:17820, 2024: 18765, 2025: 19620
}
#The following calculates the years of coverage for the special minimum guarantee.
def getYearsOfCover(inc_str:list, index_year:int):
    """ This function takes in 
        - inc_str which is the list of incs history
        - index_year which is the year associated with the first indexed inc in inc_str
        
        This function calculates the years of coverage according to pdf page 5 (or page 1333) in 1972 major pdf."""
    # Get the years_of_coverage pdf page 5 and page 1333 in 1972 major
    sum_wage_before_1951 = 0
    totalYOC = 0
    for i, earnings in enumerate(inc_str):
        current_year = index_year + i
        if current_year < 1951:
            sum_wage_before_1951 = sum_wage_before_1951 + earnings
        else:
            if earnings >= Thresholds.get(current_year):
                totalYOC = totalYOC + 1

    pre1951YOC = min(int(sum_wage_before_1951 // 900), 14) #Max 14 YOC under 1951.
    totalYOC + pre1951YOC + totalYOC
    return min(totalYOC, 30)


#This changed in 72 minor
def bb1973(income_stream:list, original_income_stream:list, avg_monthly_wage:int, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    retirement_year = index_year + len(income_stream)
    #adjusted_income_stream=i1973(inc_str, index_year)
    #avg_monthly_wage=math.floor(a1973(adjusted_income_stream, index_year, birth_year, woman))
    #print("1973 average monthly wage: ", avg_monthly_wage)
    #avg_monthly_wage = 1053
    #avg_monthly_wage = 3133
    # Remove zeros in-place
    income_stream = [value for value in income_stream if value != 0]
    pia_1971 = 0

    years_of_coverage = getYearsOfCover(income_stream, index_year)

    
    if (birth_year+65<1950): #this checks if they are old enough to have a pib; someone who did have a pib would receive a new updated pia based on these charts below, if they do they go through the formulas differently. This is what the tables primarily deal with.
        pib=b1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year,retirement_year, reference_year, woman)
    elif (birth_year+65<1973):
        pia_1971=b1971(i1971(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
  
    
    col1 = [
    [0, 16.20],       [16.21, 16.84],   [16.85, 17.60],   [17.61, 18.40],
    [18.41, 19.24],   [19.25, 20.00],   [20.01, 20.64],   [20.65, 21.28],
    [21.29, 21.88],   [21.89, 22.28],   [22.29, 22.68],   [22.69, 23.08],
    [23.09, 23.44],   [23.45, 23.76],   [23.77, 24.20],   [24.21, 24.60],
    [24.61, 25.00],   [25.01, 25.48],   [26.49, 26.92],   [25.93, 26.40],
    [26.41, 26.94],   [26.95, 27.46],   [27.47, 28.00],   [28.01, 28.68],
    [28.69, 29.25],   [29.26, 29.68],   [29.69, 30.36],   [30.37, 30.92],
    [30.93, 31.36],   [31.37, 32.00],   [32.01, 32.60],   [32.61, 33.20],
    [33.21, 33.88],   [33.89, 34.50],   [34.51, 35.00],   [35.01, 35.80],
    [35.81, 36.40],   [36.41, 37.08],   [37.09, 37.60],   [37.61, 38.20],
    [38.21, 39.12],   [39.13, 39.68],   [39.69, 40.33],   [40.34, 41.12],
    [41.13, 41.76],   [41.77, 42.44],   [42.45, 43.20],   [43.21, 43.76],
    [43.77, 44.44],   [44.45, 44.88],   [44.89, 45.60]
    ]
    
    col2 = [
    84.50, 85.80, 87.80, 89.40, 91.00, 92.90, 94.60, 96.20, 98.10, 99.80,
    101.40, 103.00, 104.90, 106.70, 108.80, 110.30, 112.10, 114.20, 116.00, 117.90,
    119.70, 121.40, 123.30, 125.10, 127.10, 128.80, 130.50, 132.50, 134.30, 136.00,
    138.00, 139.70, 141.60, 143.40, 145.20, 147.20, 148.80, 150.90, 152.70, 154.40,
    156.40, 158.20, 159.80, 161.80, 163.60, 165.50, 167.30, 169.40, 171.00, 172.70,
    174.80, 176.60, 178.10, 180.20, 182.00, 183.90, 185.70, 187.50, 189.50, 191.10,
    193.10, 194.90, 196.60, 198.60, 200.30, 202.00, 204.00, 205.80, 207.90, 209.40,
    211.20, 213.30, 215.00, 217.00, 218.70, 220.40, 222.40, 224.20, 226.20, 227.80,
    229.60, 231.60, 233.30, 235.40, 236.90, 238.60, 240.30, 242.20, 243.80, 245.40,
    247.40, 248.90, 250.60, 252.50, 254.10, 255.80, 257.40, 259.40, 260.90, 262.60,
    264.50, 266.10, 267.80, 269.70, 271.20, 272.90, 274.60, 276.40, 278.10, 279.80,
    281.70, 283.20, 284.90, 286.80, 288.40, 290.10, 291.50, 293.10, 294.60, 296.20,
    297.60, 299.20, 300.60, 302.20, 303.60, 305.30, 306.80, 308.30, 309.80, 311.30,
    312.80, 314.40, 315.90, 317.40, 318.90, 320.40, 321.90, 323.40, 325.00, 326.60,
    328.00, 329.60, 331.00, 332.00, 332.90, 334.10, 335.30, 336.50, 337.70, 338.90,
    340.10, 341.30, 342.50, 343.70, 344.90, 346.10, 347.30, 348.50, 349.70, 350.90,
    352.10, 353.30, 354.50, 355.50, 356.50, 357.50, 358.50, 359.50, 360.50, 361.50,
    362.50, 363.50, 364.50, 365.50, 366.50, 367.60, 368.60, 369.50, 370.60, 371.60,
    372.60, 373.60, 374.60, 375.50, 376.60, 377.50, 378.60, 379.50, 380.50, 381.60,
    382.60, 383.60, 384.60, 385.60, 386.50, 387.60, 388.60, 389.60, 390.60, 391.50,
    392.60, 393.60, 394.60, 395.60, 396.80, 397.60, 398.60, 399.50, 400.50, 401.60,
    402.60, 403.60, 404.60]

    col3 = [
        [0, 76], [77, 78], [79, 80], [81, 81], [82, 83],
        [84, 85], [86, 87], [88, 89], [90, 90], [91, 92],
        [93, 94], [95, 96], [97, 97], [98, 99], [100, 101],
        [102, 102], [103, 104], [105, 106], [107, 107], [108, 109],
        [110, 113], [114, 118], [119, 122], [123, 127], [128, 132],
        [133, 136], [137, 141], [142, 146], [147, 150], [151, 155],
        [156, 160], [161, 164], [165, 169], [170, 174], [175, 179],
        [179, 183], [184, 188], [189, 193], [194, 197], [198, 202],
        [203, 207], [208, 211], [212, 216], [217, 221], [222, 225],
        [226, 230], [231, 235], [236, 239], [240, 244], [245, 249],
        [250, 253], [254, 258], [259, 263], [264, 267], [268, 272],
        [273, 277], [278, 281], [282, 286], [287, 291], [292, 295],
        [296, 300], [301, 305], [306, 309], [310, 314], [315, 319],
        [320, 323], [324, 328], [329, 333], [334, 337], [338, 342],
        [343, 347], [348, 351], [352, 356], [357, 361], [362, 365],
        [366, 370], [371, 375], [376, 379], [380, 384], [385, 389],
        [390, 393], [394, 398], [399, 403], [404, 407], [408, 412],
        [413, 417], [418, 421], [422, 426], [427, 431], [432, 436],
        [437, 440], [441, 445], [446, 450], [451, 454], [455, 459],
        [460, 464], [465, 468], [469, 473], [474, 478], [479, 482],
        [483, 487], [488, 492], [493, 496], [497, 501], [502, 506],
        [507, 510], [511, 515], [516, 520], [521, 524], [525, 529],
        [530, 534], [535, 538], [539, 543], [544, 548], [549, 553],
        [554, 556], [557, 560], [561, 563], [564, 567], [568, 570],
        [571, 574], [575, 577], [578, 581], [582, 584], [585, 588],
        [589, 591], [592, 595], [596, 598], [599, 602], [603, 605],
        [606, 609], [610, 612], [613, 616], [617, 620], [621, 623],
        [624, 627], [628, 630], [631, 634], [635, 637], [638, 641],
        [642, 644], [645, 648], [649, 652], [653, 656], [657, 660],
        [661, 665], [666, 670], [671, 675], [676, 680], [681, 685],
        [686, 690], [691, 695], [696, 700], [701, 705], [706, 710],
        [711, 715], [716, 720], [721, 725], [726, 730], [731, 735],
        [736, 740], [741, 745], [746, 750], [751, 755], [756, 760],
        [761, 765], [766, 770], [771, 775], [776, 780], [781, 785],
        [786, 790], [791, 795], [796, 800], [801, 805], [806, 810],
        [811, 815], [816, 820], [821, 825], [826, 830], [831, 835],
        [836, 840], [841, 845], [846, 850], [851, 855], [856, 860],
        [861, 865], [866, 870], [871, 875], [876, 880], [881, 885],
        [886, 890], [891, 895], [896, 900], [901, 905], [906, 910],
        [911, 915], [916, 920], [921, 925], [926, 930], [931, 935],
        [936, 940], [941, 945], [946, 950], [951, 955], [956, 960],
        [961, 965], [966, 970], [971, 975], [976, 980], [981, 985],
        [986, 990], [991, 995], [996, 1000], [1001, 1005], [1006, 1010],
        [1011, 1015], [1016, 1020], [1021, 1025], [1026, 1030], [1031, 1035],
        [1036, 1040], [1041, 1045], [1046, 1050], [1051, 1055], [1056, 1060],
        [1061, 1065], [1066, 1070], [1071, 1075], [1076, 1080], [1081, 1085],
        [1086, 1090], [1091, 1095], [1096, 11010000000000000] #this is a quick fix to the problem of an avg monthly wage going over the last number in the table of 1101, now it is an effective cap on pia at 469
    ]

   

    col4 = [
    93.80,  95.30,  97.50,  99.30, 101.10,
   103.20, 105.10, 106.80, 108.90, 110.80,
   112.60, 114.40, 116.50, 118.50, 120.80,
   122.50, 124.50, 126.80, 128.80, 130.90,
   132.90, 134.80, 136.90, 138.90, 141.10,
   143.00, 144.90, 147.10, 149.10, 151.00,
   153.20, 155.10, 157.20, 159.20, 161.20,
   163.40, 165.20, 167.50, 169.50, 171.40,
   173.70, 175.70, 177.40, 179.60, 181.60,
   183.80, 185.80, 188.10, 189.90, 191.70,
   194.10, 196.10, 197.70, 200.10, 202.10,
   204.20, 206.20, 208.20, 210.40, 212.20,
   214.40, 216.40, 218.30, 220.50, 222.40,
   224.30, 226.50, 228.50, 230.80, 232.50,
   234.50, 236.80, 238.70, 240.90, 242.80,
   244.70, 246.90, 248.90, 251.10, 252.90,
   254.90, 257.10, 259.00, 261.30, 263.00,
   264.90, 266.80, 268.90, 270.70, 272.40,
   274.70, 276.30, 278.20, 280.30, 282.10,
   284.00, 285.80, 288.00, 289.60, 291.50,
   293.60, 295.40, 297.30, 299.40, 301.10,
   303.00, 304.90, 306.90, 308.70, 310.60,
   312.70, 314.40, 316.30, 318.40, 320.20,
   322.10, 323.60, 325.40, 327.10, 328.80,
   330.40, 332.20, 333.70, 335.50, 337.00,
   338.90, 340.60, 342.30, 343.90, 345.60,
   347.30, 349.00, 350.70, 352.40, 354.00,
   355.70, 357.40, 359.00, 360.80, 362.60,
   364.10, 365.90, 367.50, 368.60, 369.60,
   370.90, 372.20, 373.60, 374.90, 376.20,
   377.60, 378.90, 380.20, 381.60, 382.90,
   384.20, 385.60, 386.90, 388.20, 389.50,
   390.90, 392.20, 393.50, 394.70, 395.80,
   396.90, 398.00, 399.10, 400.20, 401.30,
   402.40, 403.50, 404.60, 405.80, 406.90,
   408.00, 409.10, 410.20, 411.30, 412.40,
   413.50, 414.60, 415.70, 416.90, 418.00,
   419.10, 420.20, 421.30, 422.40, 423.50,
   424.60, 425.70, 426.80, 428.00, 429.10,
   430.20, 431.30, 432.40, 433.50, 434.60,
   435.70, 436.80, 437.90, 439.10, 440.20,
   441.30, 442.40, 443.50, 444.60, 445.70,
   446.80, 447.90, 449.00, 450.00, 451.00,
   452.00, 453.00, 454.00, 455.00, 456.00,
   457.00, 458.00, 459.00, 460.00, 461.00,
   462.00, 463.00, 464.00, 465.00, 466.00,
   467.00, 468.00, 469.00]


    colb1976 = [[0.0, 76.0], [77.0, 78.0], [79.0, 80.0], [81.0, 81.0], [82.0, 83.0], [84.0, 85.0], [86.0, 87.0], [88.0, 89.0], [90.0, 90.0], [91.0, 92.0], [93.0, 94.0], [95.0, 96.0], [97.0, 97.0], [98.0, 99.0], [100.0, 101.0], [102.0, 102.0], [103.0, 104.0], [105.0, 106.0], [107.0, 107.0], [108.0, 109.0], [110.0, 113.0], [114.0, 118.0], [119.0, 122.0], [123.0, 127.0], [128.0, 132.0], [133.0, 136.0], [137.0, 141.0], [142.0, 146.0], [147.0, 150.0], [151.0, 155.0], [156.0, 160.0], [161.0, 164.0], [165.0, 169.0], [170.0, 174.0], [175.0, 178.0], [179.0, 183.0], [184.0, 188.0], [189.0, 193.0], [194.0, 197.0], [198.0, 202.0], [203.0, 207.0], [208.0, 211.0], [212.0, 216.0], [217.0, 221.0], [222.0, 225.0], [226.0, 230.0], [231.0, 235.0], [236.0, 239.0], [240.0, 244.0], [245.0, 249.0], [250.0, 253.0], [254.0, 258.0], [259.0, 263.0], [264.0, 267.0], [268.0, 272.0], [273.0, 277.0], [278.0, 281.0], [282.0, 286.0], [287.0, 291.0], [292.0, 295.0], [296.0, 300.0], [301.0, 305.0], [306.0, 309.0], [310.0, 314.0], [315.0, 319.0], [320.0, 323.0], [324.0, 328.0], [329.0, 333.0], [334.0, 337.0], [338.0, 342.0], [343.0, 347.0], [348.0, 351.0], [352.0, 356.0], [357.0, 361.0], [362.0, 365.0], [366.0, 370.0], [371.0, 375.0], [376.0, 379.0], [380.0, 384.0], [385.0, 389.0], [390.0, 393.0], [394.0, 398.0], [399.0, 403.0], [404.0, 407.0], [408.0, 412.0], [413.0, 417.0], [418.0, 421.0], [422.0, 426.0], [427.0, 431.0], [432.0, 436.0], [437.0, 440.0], [441.0, 445.0], [446.0, 450.0], [451.0, 454.0], [455.0, 459.0], [460.0, 464.0], [465.0, 468.0], [469.0, 473.0], [474.0, 478.0], [479.0, 482.0], [483.0, 487.0], [488.0, 492.0], [493.0, 496.0], [497.0, 501.0], [502.0, 506.0], [507.0, 510.0], [511.0, 515.0], [516.0, 520.0], [521.0, 524.0], [525.0, 529.0], [530.0, 534.0], [535.0, 538.0], [539.0, 543.0], [544.0, 548.0], [549.0, 553.0], [554.0, 556.0], [557.0, 560.0], [561.0, 563.0], [564.0, 567.0], [568.0, 570.0], [571.0, 574.0], [575.0, 577.0], [578.0, 581.0], [582.0, 584.0], [585.0, 588.0], [589.0, 591.0], [592.0, 595.0], [596.0, 598.0], [599.0, 602.0], [603.0, 605.0], [606.0, 609.0], [610.0, 612.0], [613.0, 616.0], [617.0, 620.0], [621.0, 623.0], [624.0, 627.0], [628.0, 630.0], [631.0, 634.0], [635.0, 637.0], [638.0, 641.0], [642.0, 644.0], [645.0, 648.0], [649.0, 652.0], [653.0, 656.0], [657.0, 660.0], [661.0, 665.0], [666.0, 670.0], [671.0, 675.0], [676.0, 680.0], [681.0, 685.0], [686.0, 690.0], [691.0, 695.0], [696.0, 700.0], [701.0, 705.0], [706.0, 710.0], [711.0, 715.0], [716.0, 720.0], [721.0, 725.0], [726.0, 730.0], [731.0, 735.0], [736.0, 740.0], [741.0, 745.0], [746.0, 750.0], [751.0, 755.0], [756.0, 760.0], [761.0, 765.0], [766.0, 770.0], [771.0, 775.0], [776.0, 780.0], [781.0, 785.0], [786.0, 790.0], [791.0, 795.0], [796.0, 800.0], [801.0, 805.0], [806.0, 810.0], [811.0, 815.0], [816.0, 820.0], [821.0, 825.0], [826.0, 830.0], [831.0, 835.0], [836.0, 840.0], [841.0, 845.0], [846.0, 850.0], [851.0, 855.0], [856.0, 860.0], [861.0, 865.0], [866.0, 870.0], [871.0, 875.0], [876.0, 880.0], [881.0, 885.0], [886.0, 890.0], [891.0, 895.0], [896.0, 900.0], [901.0, 905.0], [906.0, 910.0], [911.0, 915.0], [916.0, 920.0], [921.0, 925.0], [926.0, 930.0], [931.0, 935.0], [936.0, 940.0], [941.0, 945.0], [946.0, 950.0], [951.0, 955.0], [956.0, 960.0], [961.0, 965.0], [966.0, 970.0], [971.0, 975.0], [976.0, 980.0], [981.0, 985.0], [986.0, 990.0], [991.0, 995.0], [996.0, 1000.0], [1001.0, 1005.0], [1006.0, 1010.0], [1011.0, 1015.0], [1016.0, 1020.0], [1021.0, 1025.0], [1026.0, 1030.0], [1031.0, 1035.0], [1036.0, 1040.0], [1041.0, 1045.0], [1046.0, 1050.0], [1051.0, 1055.0], [1056.0, 1060.0], [1061.0, 1065.0], [1066.0, 1070.0], [1071.0, 1075.0], [1076.0, 1080.0], [1081.0, 1085.0], [1086.0, 1090.0], [1091.0, 1095.0], [1096.0, 1100.0], [1101.0, 1105.0], [1106.0, 1110.0], [1111.0, 1115.0], [1116.0, 1120.0], [1121.0, 1125.0], [1126.0, 1130.0], [1131.0, 1135.0], [1136.0, 1140.0], [1141.0, 1145.0], [1146.0, 1150.0], [1151.0, 1155.0], [1156.0, 1160.0], [1161.0, 1165.0], [1166.0, 1170.0], [1171.0, 1175.0], [1176.0, 1180.0], [1181.0, 1185.0], [1186.0, 1190.0], [1191.0, 1195.0], [1196.0, 1200.0], [1201.0, 1205.0], [1206.0, 1210.0], [1211.0, 1215.0], [1216.0, 1220.0], [1221.0, 1225.0], [1226.0, 1230.0], [1231.0, 1235.0], [1236.0, 1240.0], [1241.0, 1245.0], [1246.0, 1250.0], [1251.0, 1255.0], [1256.0, 1260.0], [1261.0, 1265.0], [1266.0, 1270.0], [1271.0, 10000000000000000]]
    colb1976 = [101.4, 103.0, 105.3, 107.3, 109.2, 111.5, 113.6, 115.4, 117.7, 119.7, 121.7, 123.6, 125.9, 128.0, 130.5, 132.3, 134.5, 137.0, 139.2, 141.4, 143.6, 145.6, 147.9, 150.1, 152.4, 154.5, 156.5, 158.9, 161.1, 163.1, 165.5, 167.6, 169.8, 172.0, 174.1, 176.5, 178.5, 180.9, 183.1, 185.2, 187.6, 189.8, 191.6, 194.0, 196.2, 198.6, 200.7, 203.2, 205.1, 207.1, 209.7, 211.8, 213.6, 216.2, 218.3, 220.6, 222.7, 224.9, 227.3, 229.2, 231.6, 233.8, 235.8, 238.2, 240.2, 242.3, 244.7, 246.8, 249.3, 251.1, 253.3, 255.8, 257.8, 260.2, 262.3, 264.3, 266.7, 268.9, 271.2, 273.2, 275.3, 277.7, 279.8, 282.3, 284.1, 286.1, 288.2, 290.5, 292.4, 294.2, 296.7, 298.5, 300.5, 302.8, 304.7, 306.8, 308.7, 311.1, 312.8, 314.9, 317.1, 319.1, 321.1, 323.4, 325.2, 327.3, 329.3, 331.5, 333.4, 335.5, 337.8, 339.6, 341.7, 343.9, 345.9, 347.9, 349.5, 351.5, 353.3, 355.2, 356.9, 358.8, 360.4, 362.4, 364.0, 366.1, 367.9, 369.7, 371.5, 373.3, 375.1, 377.0, 378.8, 380.6, 382.4, 384.2, 386.0, 387.8, 389.7, 391.7, 393.3, 395.2, 396.9, 398.1, 399.2, 400.6, 402.0, 403.5, 404.9, 406.3, 407.9, 409.3, 410.7, 412.2, 413.6, 415.0, 416.5, 417.9, 419.3, 420.7, 422.2, 423.6, 425.0, 426.3, 427.5, 428.7, 429.9, 431.1, 432.3, 433.5, 434.6, 435.8, 437.0, 438.3, 439.5, 440.7, 441.9, 443.1, 444.3, 445.4, 446.6, 447.8, 449.0, 450.3, 451.5, 452.7, 453.9, 455.1, 456.2, 457.4, 458.6, 459.8, 461.0, 462.3, 463.5, 464.7, 465.9, 467.0, 468.2, 469.4, 470.6, 471.8, 473.0, 474.3, 475.5, 476.7, 477.8, 479.0, 480.2, 481.4, 482.6, 483.8, 485.0, 486.0, 487.1, 488.2, 489.3, 490.4, 491.4, 492.5, 493.6, 494.7, 495.8, 496.8, 497.9, 499.0, 500.1, 501.2, 502.2, 503.3, 504.4, 505.5, 506.6, 507.6, 508.7, 509.8, 510.9, 512.0, 513.0, 514.1, 515.2, 516.3, 517.4, 518.4, 519.5, 520.6, 521.7, 522.8, 523.8, 524.8, 525.8, 526.8, 527.8, 528.8, 529.8, 530.8, 531.8, 532.8, 533.8, 534.8, 535.8, 536.8, 537.8, 538.8, 539.8, 540.8, 541.8, 542.8]
    
    colb1977 = [[0,76],[77.0, 78.0], [79.0, 80.0], [81.0, 81.0], [82.0, 83.0], [84.0, 85.0], [86.0, 87.0], [88.0, 89.0], [90.0, 90.0], [91.0, 92.0], [93.0, 94.0], [95.0, 96.0], [97.0, 97.0], [98.0, 99.0], [100.0, 101.0], [102.0, 102.0], [103.0, 104.0], [105.0, 106.0], [107.0, 107.0], [108.0, 109.0], [110.0, 113.0], [114.0, 118.0], [119.0, 122.0], [123.0, 127.0], [128.0, 132.0], [133.0, 136.0], [137.0, 141.0], [142.0, 146.0], [147.0, 150.0], [151.0, 155.0], [156.0, 160.0], [161.0, 164.0], [165.0, 169.0], [170.0, 174.0], [175.0, 178.0], [179.0, 183.0], [184.0, 188.0], [189.0, 193.0], [194.0, 197.0], [198.0, 202.0], [203.0, 207.0], [208.0, 211.0], [212.0, 216.0], [217.0, 221.0], [222.0, 225.0], [226.0, 230.0], [231.0, 235.0], [236.0, 239.0], [240.0, 244.0], [245.0, 249.0], [250.0, 253.0], [254.0, 258.0], [259.0, 263.0], [264.0, 267.0], [268.0, 272.0], [273.0, 277.0], [278.0, 281.0], [282.0, 286.0], [287.0, 291.0], [292.0, 295.0], [296.0, 300.0], [301.0, 305.0], [306.0, 309.0], [310.0, 314.0], [315.0, 319.0], [320.0, 323.0], [324.0, 328.0], [329.0, 333.0], [334.0, 337.0], [338.0, 342.0], [343.0, 347.0], [348.0, 351.0], [352.0, 356.0], [357.0, 361.0], [362.0, 365.0], [366.0, 370.0], [371.0, 375.0], [376.0, 379.0], [380.0, 384.0], [385.0, 389.0], [390.0, 393.0], [394.0, 398.0], [399.0, 403.0], [404.0, 407.0], [408.0, 412.0], [413.0, 417.0], [418.0, 421.0], [422.0, 426.0], [427.0, 431.0], [432.0, 436.0], [437.0, 440.0], [441.0, 445.0], [446.0, 450.0], [451.0, 454.0], [455.0, 459.0], [460.0, 464.0], [465.0, 468.0], [469.0, 473.0], [474.0, 478.0], [479.0, 482.0], [483.0, 487.0], [488.0, 492.0], [493.0, 496.0], [497.0, 501.0], [502.0, 506.0], [507.0, 510.0], [511.0, 515.0], [516.0, 520.0], [521.0, 524.0], [525.0, 529.0], [530.0, 534.0], [535.0, 538.0], [539.0, 543.0], [544.0, 548.0], [549.0, 553.0], [554.0, 556.0], [557.0, 560.0], [561.0, 563.0], [564.0, 567.0], [568.0, 570.0], [571.0, 574.0], [575.0, 577.0], [578.0, 581.0], [582.0, 584.0], [585.0, 588.0], [589.0, 591.0], [592.0, 595.0], [596.0, 598.0], [599.0, 602.0], [603.0, 605.0], [606.0, 609.0], [610.0, 612.0], [613.0, 616.0], [617.0, 620.0], [621.0, 623.0], [624.0, 627.0], [628.0, 630.0], [631.0, 634.0], [635.0, 637.0], [638.0, 641.0], [642.0, 644.0], [645.0, 648.0], [649.0, 652.0], [653.0, 656.0], [657.0, 660.0], [661.0, 665.0], [666.0, 670.0], [671.0, 675.0], [676.0, 680.0], [681.0, 685.0], [686.0, 690.0], [691.0, 695.0], [696.0, 700.0], [701.0, 705.0], [706.0, 710.0], [711.0, 715.0], [716.0, 720.0], [721.0, 725.0], [726.0, 730.0], [731.0, 735.0], [736.0, 740.0], [741.0, 745.0], [746.0, 750.0], [751.0, 755.0], [756.0, 760.0], [761.0, 765.0], [766.0, 770.0], [771.0, 775.0], [776.0, 780.0], [781.0, 785.0], [786.0, 790.0], [791.0, 795.0], [796.0, 800.0], [801.0, 805.0], [806.0, 810.0], [811.0, 815.0], [816.0, 820.0], [821.0, 825.0], [826.0, 830.0], [831.0, 835.0], [836.0, 840.0], [841.0, 845.0], [846.0, 850.0], [851.0, 855.0], [856.0, 860.0], [861.0, 865.0], [866.0, 870.0], [871.0, 875.0], [876.0, 880.0], [881.0, 885.0], [886.0, 890.0], [891.0, 895.0], [896.0, 900.0], [901.0, 905.0], [906.0, 910.0], [911.0, 915.0], [916.0, 920.0], [921.0, 925.0], [926.0, 930.0], [931.0, 935.0], [936.0, 940.0], [941.0, 945.0], [946.0, 950.0], [951.0, 955.0], [956.0, 960.0], [961.0, 965.0], [966.0, 970.0], [971.0, 975.0], [976.0, 980.0], [981.0, 985.0], [986.0, 990.0], [991.0, 995.0], [996.0, 1000.0], [1001.0, 1005.0], [1006.0, 1010.0], [1011.0, 1015.0], [1016.0, 1020.0], [1021.0, 1025.0], [1026.0, 1030.0], [1031.0, 1035.0], [1036.0, 1040.0], [1041.0, 1045.0], [1046.0, 1050.0], [1051.0, 1055.0], [1056.0, 1060.0], [1061.0, 1065.0], [1066.0, 1070.0], [1071.0, 1075.0], [1076.0, 1080.0], [1081.0, 1085.0], [1086.0, 1090.0], [1091.0, 1095.0], [1096.0, 1100.0], [1101.0, 1105.0], [1106.0, 1110.0], [1111.0, 1115.0], [1116.0, 1120.0], [1121.0, 1125.0], [1126.0, 1130.0], [1131.0, 1135.0], [1136.0, 1140.0], [1141.0, 1145.0], [1146.0, 1150.0], [1151.0, 1155.0], [1156.0, 1160.0], [1161.0, 1165.0], [1166.0, 1170.0], [1171.0, 1175.0], [1176.0, 1180.0], [1181.0, 1185.0], [1186.0, 1190.0], [1191.0, 1195.0], [1196.0, 1200.0], [1201.0, 1205.0], [1206.0, 1210.0], [1211.0, 1215.0], [1216.0, 1220.0], [1221.0, 1225.0], [1226.0, 1230.0], [1231.0, 1235.0], [1236.0, 1240.0], [1241.0, 1245.0], [1246.0, 1250.0], [1251.0, 1255.0], [1256.0, 1260.0], [1261.0, 1265.0], [1266.0, 1270.0], [1271.0, 1275.0], [1276.0, 1280.0], [1281.0, 1285.0], [1286.0, 1290.0], [1291.0, 1295.0], [1296.0, 1300.0], [1301.0, 1305.0], [1306.0, 1310.0], [1311.0, 1315.0], [1316.0, 1320.0], [1321.0, 1325.0], [1326.0, 1330.0], [1331.0, 1335.0], [1336.0, 1340.0], [1341.0, 1345.0], [1346.0, 1350.0], [1351.0, 1355.0], [1356.0, 1360.0], [1361.0, 1365.0], [1366.0, 1370.0], [1371.0, 10000000000000000]]
    colp1977 = [107.9,109.6, 112.1, 114.2, 116.2, 118.7, 120.9, 122.8, 125.3, 127.4, 129.5, 131.6, 134.0, 136.2, 138.9, 140.8, 143.2, 145.8, 148.2, 150.5, 152.8, 155.0, 157.4, 159.8, 162.2, 164.4, 166.6, 169.1, 171.5, 173.6, 176.1, 178.4, 180.7, 183.1, 185.3, 187.8, 190.0, 192.5, 194.9, 197.1, 199.7, 202.0, 203.9, 206.5, 208.8, 211.4, 213.6, 216.3, 218.3, 220.4, 223.2, 225.4, 227.3, 230.1, 232.3, 234.8, 237.0, 239.3, 241.9, 243.9, 246.5, 248.8, 250.9, 253.5, 255.6, 257.9, 260.4, 262.6, 265.3, 267.2, 269.6, 272.2, 274.3, 276.9, 279.1, 281.3, 283.8, 286.2, 288.6, 290.7, 293.0, 295.5, 297.8, 300.4, 302.3, 304.5, 306.7, 309.1, 311.2, 313.1, 315.7, 317.7, 319.8, 322.2, 324.3, 326.5, 328.5, 331.1, 332.9, 335.1, 337.4, 339.6, 341.7, 344.1, 346.1, 348.3, 350.4, 352.8, 354.8, 357.0, 359.5, 361.4, 363.6, 366.0, 368.1, 370.2, 371.9, 374.0, 376.0, 378.0, 379.8, 381.8, 383.5, 385.6, 387.3, 389.6, 391.5, 393.4, 395.3, 397.2, 399.2, 401.2, 403.1, 405.0, 406.9, 408.8, 410.8, 412.7, 414.7, 416.8, 418.5, 420.5, 422.4, 423.6, 424.8, 426.3, 427.8, 429.4, 430.9, 432.4, 434.1, 435.5, 437.0, 438.6, 440.1, 441.6, 443.2, 444.7, 446.2, 447.7, 449.3, 450.8, 452.2, 453.6, 454.9, 456.2, 457.5, 458.7, 460.0, 461.3, 462.5, 463.7, 465.0, 466.4, 467.7, 469.0, 470.2, 471.5, 472.8, 474.0, 475.2, 476.5, 477.8, 479.2, 480.4, 481.7, 483.0, 484.3, 485.4, 486.7, 488.0, 489.3, 490.6, 491.9, 493.2, 494.5, 495.8, 496.9, 498.2, 499.5, 500.8, 502.0, 503.3, 504.7, 506.0, 507.3, 508.4, 509.7, 511.0, 512.3, 513.5, 514.8, 516.1, 517.2, 518.3, 519.5, 520.7, 521.8, 522.9, 524.1, 525.2, 526.4, 527.6, 528.6, 529.8, 531.0, 532.2, 533.3, 534.4, 535.6, 536.7, 537.9, 539.1, 540.1, 541.3, 542.5, 543.6, 544.8, 545.9, 547.1, 548.2, 549.4, 550.6, 551.6, 552.8, 554.0, 555.1, 556.3, 557.4, 558.4, 559.5, 560.6, 561.6, 562.7, 563.8, 564.8, 565.9, 566.9, 568.0, 569.1, 570.1, 571.2, 572.3, 573.3, 574.4, 575.5, 576.5, 577.6, 578.6, 579.6, 580.6, 581.6, 582.6, 583.6, 584.6, 585.6, 586.6, 587.6, 588.6, 589.6, 590.6, 591.6, 592.6, 593.6, 594.6, 595.6, 596.6, 597.6]
    
    pia_under_1939 = 0
    pia_under_1971 = 0
    pia_under_avg_wage = 0
    


    if ((q1973(income_stream, original_income_stream, index_year, birth_year, retirement_year,woman)==True) and (birth_year+65<1950)):
        for rowNum in range(len(col1)):
            if pib>= col1[rowNum][0] and pib <= col1[rowNum][1]:
                pia_under_1939 = col4[rowNum]
            
        
    #get pia based on col 2 # @Daniel this hsould be based on 71 benefits we are missing a year
    if ((q1973(income_stream, original_income_stream, index_year, birth_year, retirement_year,woman)==True) and (birth_year+65<1972)):
        if pia_1971 <= col2[0]:
            pia_under_1971 = col4[0]
        else:    
            for rowNum in range(1,len(col2)): # we checked the first case. Now we check all other values
                if round(pia_1971, 2) == col2[rowNum]: # Rounded to 2 decimals
                    pia_under_1971 = col4[rowNum]

    # get pia based on co 3 avg mon wage
    #get pia based on col3
    
    for rowNum in range(len(col3)):
        #print(col3[rowNum][0], avg_monthly_wage, col3[rowNum][1], col4[rowNum])
        if avg_monthly_wage >= col3[rowNum][0] and avg_monthly_wage <= col3[rowNum][1]:
            pia_under_avg_wage = col4[rowNum]

    #1972 max, Sec 101 (a) (3), 1333, page 5 of pdf
    years_of_coverage=getYearsOfCover(income_stream, index_year)
    pia_1972= 8.50*max((years_of_coverage-10),0)
    pia = max(pia_under_1939, pia_under_1971, pia_under_avg_wage, pia_1972)
    
    return math.floor(10 * pia) / 10 #Round down to dime


# In[25]:


def b1973(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """ 
    monthly_benefits=0
    adjusted_income_stream=i1973(income_stream, index_year,retirement_year)
    nominal_total_contributions=t1973(adjusted_income_stream, index_year)


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
    elif retirement_year <= 1971: avg_monthly_wage = a1969(i1969(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1972: avg_monthly_wage=a1971(i1971(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year,retirement_year, reference_year, woman)
    elif retirement_year <= 1973: avg_monthly_wage = a1972(i1972(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    else:   avg_monthly_wage=math.floor(a1973(adjusted_income_stream, original_income_stream,  index_year, birth_year,retirement_year,reference_year,woman))


    monthly_benefits= bb1973(adjusted_income_stream, original_income_stream, avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)
    indexing_base_year = 1974
    continues = True




    if monthly_benefits == 469.00 and retirement_year >= 1975:
       if avg_monthly_wage >= 469:
        if retirement_year >= 1975:
            indexing_base_year = 1975
            if avg_monthly_wage >= 1101 and avg_monthly_wage <= 1105:
                monthly_benefits = 507.6
            elif avg_monthly_wage >= 1106 and avg_monthly_wage <= 1110:
                monthly_benefits = 508.7
            elif avg_monthly_wage >= 1111 and avg_monthly_wage <= 1115:
                monthly_benefits = 509.8
            elif avg_monthly_wage >= 1116 and avg_monthly_wage <= 1120:
                monthly_benefits = 510.9
            elif avg_monthly_wage >= 1121 and avg_monthly_wage <= 1125:
                monthly_benefits = 512
            elif avg_monthly_wage >= 1126 and avg_monthly_wage <= 1130:
                monthly_benefits = 513
            elif avg_monthly_wage >= 1131 and avg_monthly_wage <= 1135:
                monthly_benefits = 514.1
            elif avg_monthly_wage >= 1136 and avg_monthly_wage <= 1140:
                monthly_benefits = 515.2
            elif avg_monthly_wage >= 1141 and avg_monthly_wage <= 1145:
                monthly_benefits = 516.3
            elif avg_monthly_wage >= 1146 and avg_monthly_wage <= 1150:
                monthly_benefits = 517.4
            elif avg_monthly_wage >= 1151 and avg_monthly_wage <= 1155:
                monthly_benefits = 518.4
            elif avg_monthly_wage >= 1156 and avg_monthly_wage <= 1160:
                monthly_benefits = 519.5
            elif avg_monthly_wage >= 1161 and avg_monthly_wage <= 1165:
                monthly_benefits = 520.6
            elif avg_monthly_wage >= 1166 and avg_monthly_wage <= 1170:
                monthly_benefits = 521.7
            elif avg_monthly_wage >= 1171: #and avg_monthly_wage <= 1175:
                monthly_benefits = 522.8
            else: indexing_base_year = 1974
                
        if retirement_year >= 1976:
            #print("hello! ", avg_monthly_wage)
            old_indexing = indexing_base_year
            indexing_base_year = 1976
            if avg_monthly_wage >= 1176 and avg_monthly_wage <= 1180:
                monthly_benefits = 557.4
            elif avg_monthly_wage >= 1181 and avg_monthly_wage <= 1185:
                monthly_benefits = 558.4
            elif avg_monthly_wage >= 1186 and avg_monthly_wage <= 1190:
                monthly_benefits = 559.5
            elif avg_monthly_wage >= 1191 and avg_monthly_wage <= 1195:
                monthly_benefits = 560.6
            elif avg_monthly_wage >= 1196 and avg_monthly_wage <= 1200:
                monthly_benefits = 561.6
            elif avg_monthly_wage >= 1201 and avg_monthly_wage <= 1205:
                monthly_benefits = 562.7
            elif avg_monthly_wage >= 1206 and avg_monthly_wage <= 1210:
                monthly_benefits = 563.8
            elif avg_monthly_wage >= 1211 and avg_monthly_wage <= 1215:
                monthly_benefits = 564.8
            elif avg_monthly_wage >= 1216 and avg_monthly_wage <= 1220:
                monthly_benefits = 565.9
            elif avg_monthly_wage >= 1221 and avg_monthly_wage <= 1225:
                monthly_benefits = 566.9
            elif avg_monthly_wage >= 1226 and avg_monthly_wage <= 1230:
                monthly_benefits = 568
            elif avg_monthly_wage >= 1231 and avg_monthly_wage <= 1235:
                monthly_benefits = 569.1
            elif avg_monthly_wage >= 1236 and avg_monthly_wage <= 1240:
                monthly_benefits = 570.1
            elif avg_monthly_wage >= 1241 and avg_monthly_wage <= 1245:
                monthly_benefits = 571.2
            elif avg_monthly_wage >= 1246 and avg_monthly_wage <= 1250:
                monthly_benefits = 572.3
            elif avg_monthly_wage >= 1251 and avg_monthly_wage <= 1255:
                monthly_benefits = 573.3
            elif avg_monthly_wage >= 1256 and avg_monthly_wage <= 1260:
                monthly_benefits = 574.4
            elif avg_monthly_wage >= 1261 and avg_monthly_wage <= 1265:
                monthly_benefits = 575.5
            elif avg_monthly_wage >= 1266 and avg_monthly_wage <= 1270:
                monthly_benefits = 576.5
            elif avg_monthly_wage >= 1271:# and avg_monthly_wage <= 1275:
                monthly_benefits = 577.6
            else: indexing_base_year = old_indexing
        if retirement_year >= 1977:
            old_indexing = indexing_base_year
            indexing_base_year = 1977
            if avg_monthly_wage >= 1276 and avg_monthly_wage <= 1280:
                monthly_benefits = 612.8
            elif avg_monthly_wage >= 1281 and avg_monthly_wage <= 1285:
                monthly_benefits = 613.8
            elif avg_monthly_wage >= 1286 and avg_monthly_wage <= 1290:
                monthly_benefits = 614.9
            elif avg_monthly_wage >= 1291 and avg_monthly_wage <= 1295:
                monthly_benefits = 616
            elif avg_monthly_wage >= 1296 and avg_monthly_wage <= 1300:
                monthly_benefits = 617
            elif avg_monthly_wage >= 1301 and avg_monthly_wage <= 1305:
                monthly_benefits = 618.1
            elif avg_monthly_wage >= 1306 and avg_monthly_wage <= 1310:
                monthly_benefits = 619.1
            elif avg_monthly_wage >= 1311 and avg_monthly_wage <= 1315:
                monthly_benefits = 620.2
            elif avg_monthly_wage >= 1316 and avg_monthly_wage <= 1320:
                monthly_benefits = 621.3
            elif avg_monthly_wage >= 1321 and avg_monthly_wage <= 1325:
                monthly_benefits = 622.3
            elif avg_monthly_wage >= 1326 and avg_monthly_wage <= 1330:
                monthly_benefits = 623.4
            elif avg_monthly_wage >= 1331 and avg_monthly_wage <= 1335:
                monthly_benefits = 624.4
            elif avg_monthly_wage >= 1336 and avg_monthly_wage <= 1340:
                monthly_benefits = 625.5
            elif avg_monthly_wage >= 1341 and avg_monthly_wage <= 1345:
                monthly_benefits = 626.6
            elif avg_monthly_wage >= 1346 and avg_monthly_wage <= 1350:
                monthly_benefits = 627.6
            elif avg_monthly_wage >= 1351 and avg_monthly_wage <= 1355:
                monthly_benefits = 628.7
            elif avg_monthly_wage >= 1356 and avg_monthly_wage <= 1360:
                monthly_benefits = 629.7
            elif avg_monthly_wage >= 1361 and avg_monthly_wage <= 1365:
                monthly_benefits = 630.8
            elif avg_monthly_wage >= 1366 and avg_monthly_wage <= 1370:
                monthly_benefits = 631.8
            elif avg_monthly_wage >= 1371:# and avg_monthly_wage <= 1375:
                monthly_benefits = 632.9
            else: indexing_base_year = old_indexing
        if retirement_year >= 1978:
            old_indexing = indexing_base_year
            indexing_base_year = 1978
            if avg_monthly_wage >= 1376 and avg_monthly_wage <= 1380:
                monthly_benefits = 675.2
            elif avg_monthly_wage >= 1381 and avg_monthly_wage <= 1385:
                monthly_benefits = 676.2
            elif avg_monthly_wage >= 1386 and avg_monthly_wage <= 1390:
                monthly_benefits = 677.3
            elif avg_monthly_wage >= 1391 and avg_monthly_wage <= 1395:
                monthly_benefits = 678.3
            elif avg_monthly_wage >= 1396 and avg_monthly_wage <= 1400:
                monthly_benefits = 679.4
            elif avg_monthly_wage >= 1401 and avg_monthly_wage <= 1405:
                monthly_benefits = 680.5
            elif avg_monthly_wage >= 1406 and avg_monthly_wage <= 1410:
                monthly_benefits = 681.5
            elif avg_monthly_wage >= 1411 and avg_monthly_wage <= 1415:
                monthly_benefits = 682.6
            elif avg_monthly_wage >= 1416 and avg_monthly_wage <= 1420:
                monthly_benefits = 683.7
            elif avg_monthly_wage >= 1421 and avg_monthly_wage <= 1425:
                monthly_benefits = 684.7
            elif avg_monthly_wage >= 1426 and avg_monthly_wage <= 1430:
                monthly_benefits = 685.8
            elif avg_monthly_wage >= 1431 and avg_monthly_wage <= 1435:
                monthly_benefits = 686.9
            elif avg_monthly_wage >= 1436 and avg_monthly_wage <= 1440:
                monthly_benefits = 687.9
            elif avg_monthly_wage >= 1441 and avg_monthly_wage <= 1445:
                monthly_benefits = 689
            elif avg_monthly_wage >= 1446 and avg_monthly_wage <= 1450:
                monthly_benefits = 690.1
            elif avg_monthly_wage >= 1451 and avg_monthly_wage <= 1455:
                monthly_benefits = 691.1
            elif avg_monthly_wage >= 1456 and avg_monthly_wage <= 1460:
                monthly_benefits = 692.2
            elif avg_monthly_wage >= 1461 and avg_monthly_wage <= 1465:
                monthly_benefits = 693.3
            elif avg_monthly_wage >= 1466 and avg_monthly_wage <= 1470:
                monthly_benefits = 694.3
            elif avg_monthly_wage >= 1471:# and avg_monthly_wage <= 1475:
                monthly_benefits = 695.4
            else: indexing_base_year = old_indexing

        if retirement_year >= 1979:
            old_indexing = indexing_base_year
            boundaries = [[1476.0, 1480.0], [1481.0, 1485.0], [1486.0, 1490.0], [1491.0, 1495.0], [1496.0, 1500.0], [1501.0, 1505.0], [1506.0, 1510.0], [1511.0, 1515.0], [1516.0, 1520.0], [1521.0, 1525.0], [1526.0, 1530.0], [1531.0, 1535.0], [1536.0, 1540.0], [1541.0, 1545.0], [1546.0, 1550.0], [1551.0, 1555.0], [1556.0, 1560.0], [1561.0, 1565.0], [1566.0, 1570.0], [1571.0, 1575.0], [1576.0, 1580.0], [1581.0, 1585.0], [1586.0, 1590.0], [1591.0, 1595.0], [1596.0, 1600.0], [1601.0, 1605.0], [1606.0, 1610.0], [1611.0, 1615.0], [1616.0, 1620.0], [1621.0, 1625.0], [1626.0, 1630.0], [1631.0, 1635.0], [1636.0, 1640.0], [1641.0, 1645.0], [1646.0, 1650.0], [1651.0, 1655.0], [1656.0, 1660.0], [1661.0, 1665.0], [1666.0, 1670.0], [1671.0, 1675.0], [1676.0, 1680.0], [1681.0, 1685.0], [1686.0, 1690.0], [1691.0, 1695.0], [1696.0, 1700.0], [1701.0, 1705.0], [1706.0, 1710.0], [1711.0, 1715.0], [1716.0, 1720.0], [1721.0, 1725.0], [1726.0, 1730.0], [1731.0, 1735.0], [1736.0, 1740.0], [1741.0, 1745.0], [1746.0, 1750.0], [1751.0, 1755.0], [1756.0, 1760.0], [1761.0, 1765.0], [1766.0, 1770.0], [1771.0, 1775.0], [1776.0, 1780.0], [1781.0, 1785.0], [1786.0, 1790.0], [1791.0, 1795.0], [1796.0, 1800.0], [1801.0, 1805.0], [1806.0, 1810.0], [1811.0, 1815.0], [1816.0, 1820.0], [1821.0, 1825.0], [1826.0, 1830.0], [1831.0, 1835.0], [1836.0, 1840.0], [1841.0, 1845.0], [1846.0, 1850.0], [1851.0, 1855.0], [1856.0, 1860.0], [1861.0, 1865.0], [1866.0, 1870.0], [1871.0, 1875.0], [1876.0, 1880.0], [1881.0, 1885.0], [1886.0, 1890.0], [1891.0, 1895.0], [1896.0, 1900.0], [1901.0, 1905.0], [1906.0, 100000000000000]]
            benefits = [765.4, 766.5, 767.6, 768.7, 769.8, 770.9, 772.0, 773.1, 774.2, 775.3, 776.4, 777.5, 778.6, 779.7, 780.8, 781.9, 783.0, 784.1, 785.2, 786.3, 787.4, 788.5, 789.6, 790.7, 791.8, 792.9, 794.0, 795.1, 796.2, 797.3, 798.4, 799.5, 800.6, 801.7, 802.8, 803.9, 805.0, 806.1, 807.2, 808.3, 809.4, 810.5, 811.6, 812.7, 813.7, 814.8, 815.9, 817.0, 818.1, 819.2, 820.3, 821.4, 822.5, 823.6, 824.7, 825.8, 826.9, 828.0, 829.1, 830.2, 831.3, 832.4, 833.5, 834.6, 835.7, 836.8, 837.9, 839.0, 840.1, 841.2, 842.3, 843.4, 844.5, 845.6, 846.7, 847.8, 848.9, 850.0, 851.1, 852.2, 853.3, 854.4, 855.5, 856.6, 857.7, 858.8, 859.9]
            for rowNum in range(len(boundaries)):
                
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1979
                    break
                else:
                    indexing_base_year = old_indexing
        if retirement_year >= 1980:
            old_indexing = indexing_base_year
            boundaries = [[1911.0, 1915.0], [1916.0, 1920.0], [1921.0, 1925.0], [1926.0, 1930.0], [1931.0, 1935.0], [1936.0, 1940.0], [1941.0, 1945.0], [1946.0, 1950.0], [1951.0, 1955.0], [1956.0, 1960.0], [1961.0, 1965.0], [1966.0, 1970.0], [1971.0, 1975.0], [1976.0, 1980.0], [1981.0, 1985.0], [1986.0, 1990.0], [1991.0, 1995.0], [1996.0, 2000.0], [2001.0, 2005.0], [2006.0, 2010.0], [2011.0, 2015.0], [2016.0, 2020.0], [2021.0, 2025.0], [2026.0, 2030.0], [2031.0, 2035.0], [2036.0, 2040.0], [2041.0, 2045.0], [2046.0, 2050.0], [2051.0, 2055.0], [2056.0, 2060.0], [2061.0, 2065.0], [2066.0, 2070.0], [2071.0, 2075.0], [2076.0, 2080.0], [2081.0, 2085.0], [2086.0, 2090.0], [2091.0, 2095.0], [2096.0, 2100.0], [2101.0, 2105.0], [2106.0, 2110.0], [2111.0, 2115.0], [2116.0, 2120.0], [2121.0, 2125.0], [2126.0, 2130.0], [2131.0, 2135.0], [2136.0, 2140.0], [2141.0, 2145.0], [2146.0, 2150.0], [2151.0, 2155.0], [2156.0, 1000000000000]]
            benefits = [984.1, 985.2, 986.3, 987.5, 988.6, 989.8, 990.9, 992.1, 993.2, 994.3, 995.5, 996.6, 997.8, 998.9, 1000.1, 1001.2, 1002.3, 1003.5, 1004.6, 1005.8, 1006.9, 1008.1, 1009.2, 1010.3, 1011.5, 1012.6, 1013.8, 1014.9, 1016.1, 1017.2, 1018.3, 1019.5, 1020.6, 1021.8, 1022.9, 1024.1, 1025.2, 1026.3, 1027.5, 1028.6, 1029.8, 1030.9, 1032.1, 1033.2, 1034.4, 1035.5, 1036.6, 1037.8, 1038.9, 1040.1]
            for rowNum in range(len(boundaries)):
                
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1980
                    break
                else:
                    indexing_base_year = old_indexing
        if retirement_year >= 1981:
            old_indexing = indexing_base_year
            boundaries = [[2161.0, 2165.0], [2166.0, 2170.0], [2171.0, 2175.0], [2176.0, 2180.0], [2181.0, 2185.0], [2186.0, 2190.0], [2191.0, 2195.0], [2196.0, 2200.0], [2201.0, 2205.0], [2206.0, 2210.0], [2211.0, 2215.0], [2216.0, 2220.0], [2221.0, 2225.0], [2226.0, 2230.0], [2231.0, 2235.0], [2236.0, 2240.0], [2241.0, 2245.0], [2246.0, 2250.0], [2251.0, 2255.0], [2256.0, 2260.0], [2261.0, 2265.0], [2266.0, 2270.0], [2271.0, 2275.0], [2276.0, 2280.0], [2281.0, 2285.0], [2286.0, 2290.0], [2291.0, 2295.0], [2296.0, 2300.0], [2301.0, 2305.0], [2306.0, 2310.0], [2311.0, 2315.0], [2316.0, 2320.0], [2321.0, 2325.0], [2326.0, 2330.0], [2331.0, 2335.0], [2336.0, 2340.0], [2341.0, 2345.0], [2346.0, 2350.0], [2351.0, 2355.0], [2356.0, 2360.0], [2361.0, 2365.0], [2366.0, 2370.0], [2371.0, 2375.0], [2376.0, 2380.0], [2381.0, 2385.0], [2386.0, 2390.0], [2391.0, 2395.0], [2396.0, 2400.0], [2401.0, 2405.0], [2406.0, 2410.0], [2411.0, 2415.0], [2416.0, 2420.0], [2421.0, 2425.0], [2426.0, 2430.0], [2431.0, 2435.0], [2436.0, 2440.0], [2441.0, 2445.0], [2446.0, 2450.0], [2451.0, 2455.0], [2456.0, 2460.0], [2461.0, 2465.0], [2466.0, 2470.0], [2471.0, 100000000000]]
            benefits = [1157.8, 1158.9, 1160.0, 1161.1, 1162.2, 1163.3, 1164.4, 1165.5, 1166.6, 1167.8, 1168.9, 1170.0, 1171.1, 1172.2, 1173.3, 1174.4, 1175.5, 1176.7, 1177.8, 1178.9, 1180.0, 1181.1, 1182.2, 1183.3, 1184.4, 1185.6, 1186.7, 1187.8, 1188.9, 1190.0, 1191.1, 1192.2, 1193.3, 1194.4, 1195.6, 1196.7, 1197.8, 1198.9, 1200.0, 1201.1, 1202.2, 1203.3, 1204.5, 1205.6, 1206.7, 1207.8, 1208.9, 1210.0, 1211.1, 1212.2, 1213.4, 1214.5, 1215.6, 1216.7, 1217.8, 1218.9, 1220.0, 1221.1, 1222.2, 1223.4, 1224.5, 1225.6, 1226.7]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1981
                    break
                else:
                    indexing_base_year = old_indexing
        if retirement_year >= 1982:
            old_indexing = indexing_base_year
            boundaries = [[2476.0, 2480.0], [2481.0, 2485.0], [2486.0, 2490.0], [2491.0, 2495.0], [2496.0, 2500.0], [2501.0, 2505.0], [2506.0, 2510.0], [2511.0, 2515.0], [2516.0, 2520.0], [2521.0, 2525.0], [2526.0, 2530.0], [2531.0, 2535.0], [2536.0, 2540.0], [2541.0, 2545.0], [2546.0, 2550.0], [2551.0, 2555.0], [2556.0, 2560.0], [2561.0, 2565.0], [2566.0, 2570.0], [2571.0, 2575.0], [2576.0, 2580.0], [2581.0, 2585.0], [2586.0, 2590.0], [2591.0, 2595.0], [2596.0, 2600.0], [2601.0, 2605.0], [2606.0, 2610.0], [2611.0, 2615.0], [2616.0, 2620.0], [2621.0, 2625.0], [2626.0, 2630.0], [2631.0, 2635.0], [2636.0, 2640.0], [2641.0, 2645.0], [2646.0, 2650.0], [2651.0, 2655.0], [2656.0, 2660.0], [2661.0, 2665.0], [2666.0, 2670.0], [2671.0, 2675.0], [2676.0, 2680.0], [2681.0, 2685.0], [2686.0, 2690.0], [2691.0, 2695.0], [2696.0, 100000000000]]
            benefits = [1318.5, 1319.6, 1320.6, 1321.7, 1322.8, 1323.9, 1324.9, 1326.0, 1327.1, 1328.2, 1329.2, 1330.3, 1331.4, 1332.5, 1333.5, 1334.6, 1335.7, 1336.8, 1337.8, 1338.9, 1340.0, 1341.1, 1342.1, 1343.2, 1344.3, 1345.3, 1346.4, 1347.5, 1348.6, 1349.6, 1350.7, 1351.8, 1352.9, 1353.9, 1355.0, 1356.1, 1357.2, 1358.2, 1359.3, 1360.4, 1361.5, 1362.5, 1363.6, 1364.7, 1365.8]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1982
                    break
                else:
                    indexing_base_year = old_indexing
        
        if retirement_year >= 1983:
            old_indexing = indexing_base_year
            boundaries = [[2706.0, 2710.0], [2711.0, 2715.0], [2716.0, 2720.0], [2721.0, 2725.0], [2726.0, 2730.0], [2731.0, 2735.0], [2736.0, 2740.0], [2741.0, 2745.0], [2746.0, 2750.0], [2751.0, 2755.0], [2756.0, 2760.0], [2761.0, 2765.0], [2766.0, 2770.0], [2771.0, 2775.0], [2776.0, 2780.0], [2781.0, 2785.0], [2786.0, 2790.0], [2791.0, 2795.0], [2796.0, 2800.0], [2801.0, 2805.0], [2806.0, 2810.0], [2811.0, 2815.0], [2816.0, 2820.0], [2821.0, 2825.0], [2826.0, 2830.0], [2831.0, 2835.0], [2836.0, 2840.0], [2841.0, 2845.0], [2846.0, 2850.0], [2851.0, 2855.0], [2856.0, 2860.0], [2861.0, 2865.0], [2866.0, 2870.0], [2871.0, 2875.0], [2876.0, 2880.0], [2881.0, 2885.0], [2886.0, 2890.0], [2891.0, 2895.0], [2896.0, 2900.0], [2901.0, 2905.0], [2906.0, 2910.0], [2911.0, 2915.0], [2916.0, 2920.0], [2921.0, 2925.0], [2926.0, 2930.0], [2931.0, 2935.0], [2936.0, 2940.0], [2941.0, 2945.0], [2946.0, 2950.0], [2951.0, 2955.0], [2956.0, 2960.0], [2961.0, 2965.0], [2966.0, 2970.0], [2971.0, 100000000000000]]
            benefits = [1415.6, 1416.7, 1417.7, 1418.7, 1419.8, 1420.8, 1421.8, 1422.9, 1423.9, 1424.9, 1426.0, 1427.0, 1428.0, 1429.1, 1430.1, 1431.1, 1432.2, 1433.2, 1434.3, 1435.3, 1436.3, 1437.4, 1438.4, 1439.4, 1440.5, 1441.5, 1442.5, 1443.6, 1444.6, 1445.6, 1446.7, 1447.7, 1448.7, 1449.8, 1450.8, 1451.8, 1452.9, 1453.9, 1455.0, 1456.0, 1457.0, 1458.1, 1459.1, 1460.1, 1461.2, 1462.2, 1463.2, 1464.3, 1465.3, 1466.3, 1467.4, 1468.4, 1469.4, 1470.5]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1983
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1984:
            old_indexing = indexing_base_year
            boundaries = [[2976.0, 2980.0], [2981.0, 2985.0], [2986.0, 2990.0], [2991.0, 2995.0], [2996.0, 3000.0], [3001.0, 3005.0], [3006.0, 3010.0], [3011.0, 3015.0], [3016.0, 3020.0], [3021.0, 3025.0], [3026.0, 3030.0], [3031.0, 3035.0], [3036.0, 3040.0], [3041.0, 3045.0], [3046.0, 3050.0], [3051.0, 3055.0], [3056.0, 3060.0], [3061.0, 3065.0], [3066.0, 3070.0], [3071.0, 3075.0], [3076.0, 3080.0], [3081.0, 3085.0], [3086.0, 3090.0], [3091.0, 3095.0], [3096.0, 3100.0], [3101.0, 3105.0], [3106.0, 3110.0], [3111.0, 3115.0], [3116.0, 3120.0], [3121.0, 3125.0], [3126.0, 3130.0], [3131.0, 3135.0], [3136.0, 3140.0], [3141.0, 3145.0], [3146.0, 10000000000000000]]
            benefits = [1523.0, 1524.0, 1525.0, 1526.1, 1527.1, 1528.1, 1529.2, 1530.2, 1531.2, 1532.3, 1533.3, 1534.3, 1535.4, 1536.4, 1537.4, 1538.5, 1539.5, 1540.5, 1541.6, 1542.6, 1543.7, 1544.7, 1545.7, 1546.8, 1547.8, 1548.8, 1549.9, 1550.9, 1551.9, 1553.0, 1554.0, 1555.0, 1556.1, 1557.1, 1558.1]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1984
                    break
                else:
                    indexing_base_year = old_indexing
        
        if retirement_year >= 1985:
            old_indexing = indexing_base_year
            boundaries = [[3156.0, 3160.0], [3161.0, 3165.0], [3166.0, 3170.0], [3171.0, 3175.0], [3176.0, 3180.0], [3181.0, 3185.0], [3186.0, 3190.0], [3191.0, 3195.0], [3196.0, 3200.0], [3201.0, 3205.0], [3206.0, 3210.0], [3211.0, 3215.0], [3216.0, 3220.0], [3221.0, 3225.0], [3226.0, 3230.0], [3231.0, 3235.0], [3236.0, 3240.0], [3241.0, 3245.0], [3246.0, 3250.0], [3251.0, 3255.0], [3256.0, 3260.0], [3261.0, 3265.0], [3266.0, 3270.0], [3271.0, 3275.0], [3276.0, 3280.0], [3281.0, 3285.0], [3286.0, 3290.0], [3291.0, 3295.0], [3296.0, 10000000000000000]]
            benefits = [1608.4, 1609.4, 1610.5, 1611.5, 1612.5, 1613.6, 1614.6, 1615.6, 1616.7, 1617.7, 1618.7, 1619.8, 1620.8, 1621.8, 1622.8, 1623.9, 1624.9, 1625.9, 1627.0, 1628.0, 1629.0, 1630.1, 1631.1, 1632.1, 1633.2, 1634.2, 1635.2, 1636.3, 1637.3]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1985
                    break
                else:
                    indexing_base_year = old_indexing
        
        if retirement_year >= 1986:
            old_indexing = indexing_base_year
            boundaries = [[3306.0, 3310.0], [3311.0, 3315.0], [3316.0, 3320.0], [3321.0, 3325.0], [3326.0, 3330.0], [3331.0, 3335.0], [3336.0, 3340.0], [3341.0, 3345.0], [3346.0, 3350.0], [3351.0, 3355.0], [3356.0, 3360.0], [3361.0, 3365.0], [3366.0, 3370.0], [3371.0, 3375.0], [3376.0, 3380.0], [3381.0, 3385.0], [3386.0, 3390.0], [3391.0, 3395.0], [3396.0, 3400.0], [3401.0, 3405.0], [3406.0, 3410.0], [3411.0, 3415.0], [3416.0, 3420.0], [3421.0, 3425.0], [3426.0, 3430.0], [3431.0, 3435.0], [3436.0, 3440.0], [3441.0, 3445.0], [3446.0, 3450.0], [3451.0, 3455.0], [3456.0, 3460.0], [3461.0, 3465.0], [3466.0, 3470.0], [3471.0, 3475.0], [3476.0, 3480.0], [3481.0, 3485.0], [3486.0, 3490.0], [3491.0, 3495.0], [3496.0, 10000000000000000]]
            benefits = [1660.6, 1661.6, 1662.6, 1663.6, 1664.6, 1665.6, 1666.6, 1667.7, 1668.7, 1669.7, 1670.7, 1671.7, 1672.7, 1673.7, 1674.7, 1675.8, 1676.8, 1677.8, 1678.8, 1679.8, 1680.8, 1681.8, 1682.8, 1683.9, 1684.9, 1685.9, 1686.9, 1687.9, 1688.9, 1689.9, 1691.0, 1692.0, 1693.0, 1694.0, 1695.0, 1696.0, 1697.0, 1698.0, 1699.1]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1986
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1987:
            old_indexing = indexing_base_year
            boundaries =[[3506.0, 3510.0], [3511.0, 3515.0], [3516.0, 3520.0], [3521.0, 3525.0], [3526.0, 3530.0], [3531.0, 3535.0], [3536.0, 3540.0], [3541.0, 3545.0], [3546.0, 3550.0], [3551.0, 3555.0], [3556.0, 3560.0], [3561.0, 3565.0], [3566.0, 3570.0], [3571.0, 3575.0], [3576.0, 3580.0], [3581.0, 3585.0], [3586.0, 3590.0], [3591.0, 3595.0], [3596.0, 3600.0], [3601.0, 3605.0], [3606.0, 3610.0], [3611.0, 3615.0], [3616.0, 3620.0], [3621.0, 3625.0], [3626.0, 3630.0], [3631.0, 3635.0], [3636.0, 3640.0], [3641.0, 3645.0], [3646.0, 1000000000000000]]
            benefits = [1772.5, 1773.5, 1774.6, 1775.6, 1776.7, 1777.7, 1778.7, 1779.8, 1780.8, 1781.9, 1782.9, 1784.0, 1785.0, 1786.0, 1787.1, 1788.1, 1789.2, 1790.2, 1791.3, 1792.3, 1793.3, 1794.4, 1795.4, 1796.5, 1797.5, 1798.5, 1799.6, 1800.6, 1801.7]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1987
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1988:
            old_indexing = indexing_base_year
            boundaries =[[3656.0, 3660.0], [3661.0, 3665.0], [3666.0, 3670.0], [3671.0, 3675.0], [3676.0, 3680.0], [3681.0, 3685.0], [3686.0, 3690.0], [3691.0, 3695.0], [3696.0, 3700.0], [3701.0, 3705.0], [3706.0, 3710.0], [3711.0, 3715.0], [3716.0, 3720.0], [3721.0, 3725.0], [3726.0, 3730.0], [3731.0, 3735.0], [3736.0, 3740.0], [3741.0, 3745.0], [3746.0, 1000000000000000000]]
            benefits = [1875.8, 1876.8, 1877.9, 1878.9, 1880.0, 1881.0, 1882.0, 1883.1, 1884.1, 1885.2, 1886.2, 1887.2, 1888.3, 1889.3, 1890.4, 1891.4, 1892.4, 1893.5, 1894.5]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1988
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1989:
            old_indexing = indexing_base_year
            boundaries =[[3756.0, 3760.0], [3761.0, 3765.0], [3766.0, 3770.0], [3771.0, 3775.0], [3776.0, 3780.0], [3781.0, 3785.0], [3786.0, 3790.0], [3791.0, 3795.0], [3796.0, 3800.0], [3801.0, 3805.0], [3806.0, 3810.0], [3811.0, 3815.0], [3816.0, 3820.0], [3821.0, 3825.0], [3826.0, 3830.0], [3831.0, 3835.0], [3836.0, 3840.0], [3841.0, 3845.0], [3846.0, 3850.0], [3851.0, 3855.0], [3856.0, 3860.0], [3861.0, 3865.0], [3866.0, 3870.0], [3871.0, 3875.0], [3876.0, 3880.0], [3881.0, 3885.0], [3886.0, 3890.0], [3891.0, 3895.0], [3896.0, 3900.0], [3901.0, 3905.0], [3906.0, 3910.0], [3911.0, 3915.0], [3916.0, 3920.0], [3921.0, 3925.0], [3926.0, 3930.0], [3931.0, 3935.0], [3936.0, 3940.0], [3941.0, 3945.0], [3946.0, 3950.0], [3951.0, 3955.0], [3956.0, 3960.0], [3961.0, 3965.0], [3966.0, 3970.0], [3971.0, 3975.0], [3976.0, 3980.0], [3981.0, 3985.0], [3986.0, 3990.0], [3991.0, 3995.0], [3996.0, 10000000000000000.0]]
            benefits = [1985.6, 1986.6, 1987.7, 1988.7, 1989.8, 1990.8, 1991.9, 1992.9, 1994.0, 1995.0, 1996.1, 1997.1, 1998.1, 1999.2, 2000.2, 2001.3, 2002.3, 2003.4, 2004.4, 2005.5, 2006.5, 2007.6, 2008.6, 2009.7, 2010.7, 2011.8, 2012.8, 2013.9, 2014.9, 2015.9, 2017.0, 2018.0, 2019.1, 2020.1, 2021.2, 2022.2, 2023.3, 2024.3, 2025.4, 2026.4, 2027.5, 2028.5, 2029.6, 2030.6, 2031.7, 2032.7, 2033.7, 2034.8, 2035.8]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1989
                    break
                else:
                    indexing_base_year = old_indexing
    
    for i in range(indexing_base_year + 1,reference_year):
        #print(i, " applied: ", cola_adjustments[i+1], " and ", indexed_monthly_benefits*(1+cola_adjustments[i+1]))
        cola = (1+cola_adjustments[i+1]) 
        if i == 1999 and retirement_year > 2001: 
            cola = 1.025 #Pursuant to Public Law 106-554
        
        monthly_benefits*=cola #this is actually not quite right, this smoothes how the adjustments are actually done seen on pages 7 and 8 of pdf, this actually probably produces a positive bias on long time scales of benefits paid outs
        monthly_benefits = round(monthly_benefits,4)
        if i < 1982:
            monthly_benefits = math.ceil(monthly_benefits * 10) / 10
        else:
            monthly_benefits = math.floor(monthly_benefits * 10) / 10

    
    nra = 65
    age_at_retirement = retirement_year - birth_year

    
    if age_at_retirement < nra:
        # Early retirement deduction: 0.556% per month early
        early_deduction = 12 * 0.00556 * (nra - age_at_retirement)
        monthly_benefits = (1 - early_deduction) * monthly_benefits
    elif age_at_retirement > nra:
        ageAtIndex = index_year - birth_year
        prevnra = nra
        #print("age: ", nra - ageAtIndex+1)
        tempRetirementAge = max(0,nra - ageAtIndex+1)
        relevantInct = income_stream[0:tempRetirementAge]
        while not q1973(relevantInct,original_income_stream, index_year, birth_year,retirement_year,woman):
            
            nra +=1
            #print("year", birth_year + nra)
            tempRetirementAge = max(0,nra - ageAtIndex+1)
            relevantInct = income_stream[0:tempRetirementAge]
        effective_start = max(birth_year + nra, 1971)
        
        quarterInWhichQEligible, yearInWhichQEligible = getQYYYQuarterQualified(relevantInct, index_year, birth_year, woman) #if 0, then Q4, so 3 months. If 1, then Q3, so 6 months. if 2, then Q2, so 9 months
        #print(quarterInWhichQEligible, yearInWhichQEligible)
        #print(quarterInWhichQEligible, yearInWhichQEligible, prevnra+birth_year, effective_start)
        years_delayed = 0
        if yearInWhichQEligible < prevnra + birth_year or yearInWhichQEligible > birth_year + 70 or yearInWhichQEligible < 1971: extraMonthsEligible = 0
        elif yearInWhichQEligible == prevnra + birth_year and quarterInWhichQEligible == 1: extraMonthsEligible = 0
        else:
            if yearInWhichQEligible >= prevnra+birth_year and quarterInWhichQEligible != 1:
                years_delayed = years_delayed -1
                extraMonthsEligible = (4-quarterInWhichQEligible)*3 + 3 #If 4, then 3. If 3, then 6. If 2, then 9. If 1, then 12

            else: extraMonthsEligible = 0
        
        #print(effective_start)
        for year in range(effective_start, retirement_year):
            if year < 1984 and year - birth_year <= 72 - 1:
                years_delayed += 1 
                #print(year)
            elif year >= 1984 and year - birth_year <= 70 -1:
                years_delayed +=1
                #print(year)
        late_credit = (0.01)/(12) * max(0,(12*years_delayed + extraMonthsEligible))
        #print("years: ", years_delayed)
        #print("months: ", (12*years_delayed + extraMonthsEligible))
        #print("late: ", late_credit)
        #late_credit = 0

        #print("avg: ", avg_monthly_wage)
        #print("monthly: ", monthly_benefits)

        '''
        effective_end   = min(1984,retirement_year, birth_year + 72)

        actualCredit_years = max(effective_end - effective_start, 0)

        #if retirement_year <= 1983:
        actualCredit_years = min(7, actualCredit_years)
        #else:
        #    actualCredit_years = min(5, actualCredit_years)
        print(actualCredit_years)
        #print(nra)
        late_credit = 0.01 * actualCredit_years'''

        '''
       elif age_at_retirement > nra:
        # Delayed retirement credit, starting from 1971 and capped at age 72
        if retirement_year <= 1983:
            max_credit_year = min(birth_year + 72, retirement_year) 
        else:
            #print("hello! ", monthly_benefits)
            max_credit_year = min(birth_year + 70, retirement_year) #The 1983 Amendments capped late credits to 70 for all cohorts
        print(max_credit_year)
        effective_start_year = max(birth_year + nra, 1971)
        print(effective_start_year)
        actual_credit_years = max(max_credit_year - effective_start_year, 0)
    
        late_credit = 0.01 * actual_credit_years
        print(late_credit)
        #late_credit = 0'''
        #print(1+late_credit)
        #print("pre-mont: ", monthly_benefits)
        #print("late ", late_credit)
        monthly_benefits = (1 + late_credit) * monthly_benefits
        #print(monthly_benefits)
    #############

     #explain how the inflation function works

    #print(indexed_monthly_benefits)

    #print("indexed_monthly_benefits: ", indexed_monthly_benefits)
    #print("monthly: ", monthly_benefits)
    if reference_year >= 1983:
        return math.floor(monthly_benefits)
    elif reference_year >= 1977:
        return math.ceil(monthly_benefits * 10) / 10
    else:
        return math.ceil(10*monthly_benefits) /10


# pdf page 8 and 9 of 1973. Note that they report full OASDI taxes, not just OASI, so DI must be subtracted from them.
#note that disability insurance taxes is now active, these can be found on page 9-10 of 1973 pdf 
def t1973(income_stream:list, index_year:int):
    
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    adjusted_income_stream=i1973(income_stream, index_year, len(income_stream) + index_year) #to apply the taxable maximums to the benefit stream
    
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
        if (index_year+i) >=1978 and (index_year+i) <=1980: 
             employee_tax_rate= 0.0435
             employer_tax_rate= 0.0435
             disability_tax=.012
        if (index_year+i) >=1981 and (index_year+i) <=1985: 
             employee_tax_rate= 0.043
             employer_tax_rate= 0.043
             disability_tax=.013
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1986 and (index_year+i) <=2010: 
             employee_tax_rate= 0.0420
             employer_tax_rate= 0.0420
             disability_tax=.015
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=2011: 
             employee_tax_rate= 0.052
             employer_tax_rate= 0.052
             disability_tax=.015
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
    return nominal_contributions



def death1973(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    woman: This is TRUE if the deceased was female.
    '''
    if (q1971(income_stream, index_year, birth_year)): 
        monthlyBenefits = b1973(income_stream, index_year, birth_year, retirement_year, woman)
        return max(3 * monthlyBenefits, 255)
    else:
        return 0
    

def spouse1973(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    if q1973(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_woman):
        spouse_benefit = b1973(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    primary_adjusted_income_stream=i1973(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1973(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)

    #print("primary: ", primary_avg_monthly_wage)

    primary_PIA = bb1973(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)

    #print("primaryPIA: ", primary_PIA)

    deduction = 1
    indexing_base_year = 1974
    avg_monthly_wage = primary_avg_monthly_wage
    monthly_benefits = primary_PIA
    if monthly_benefits == 469.00 and retirement_year >= 1975:
       if avg_monthly_wage >= 469:
        if retirement_year >= 1975:
            indexing_base_year = 1975
            if avg_monthly_wage >= 1101 and avg_monthly_wage <= 1105:
                monthly_benefits = 507.6
            elif avg_monthly_wage >= 1106 and avg_monthly_wage <= 1110:
                monthly_benefits = 508.7
            elif avg_monthly_wage >= 1111 and avg_monthly_wage <= 1115:
                monthly_benefits = 509.8
            elif avg_monthly_wage >= 1116 and avg_monthly_wage <= 1120:
                monthly_benefits = 510.9
            elif avg_monthly_wage >= 1121 and avg_monthly_wage <= 1125:
                monthly_benefits = 512
            elif avg_monthly_wage >= 1126 and avg_monthly_wage <= 1130:
                monthly_benefits = 513
            elif avg_monthly_wage >= 1131 and avg_monthly_wage <= 1135:
                monthly_benefits = 514.1
            elif avg_monthly_wage >= 1136 and avg_monthly_wage <= 1140:
                monthly_benefits = 515.2
            elif avg_monthly_wage >= 1141 and avg_monthly_wage <= 1145:
                monthly_benefits = 516.3
            elif avg_monthly_wage >= 1146 and avg_monthly_wage <= 1150:
                monthly_benefits = 517.4
            elif avg_monthly_wage >= 1151 and avg_monthly_wage <= 1155:
                monthly_benefits = 518.4
            elif avg_monthly_wage >= 1156 and avg_monthly_wage <= 1160:
                monthly_benefits = 519.5
            elif avg_monthly_wage >= 1161 and avg_monthly_wage <= 1165:
                monthly_benefits = 520.6
            elif avg_monthly_wage >= 1166 and avg_monthly_wage <= 1170:
                monthly_benefits = 521.7
            elif avg_monthly_wage >= 1171: #and avg_monthly_wage <= 1175:
                monthly_benefits = 522.8
            else: indexing_base_year = 1974
                
        if retirement_year >= 1976:
            #print("hello! ", avg_monthly_wage)
            old_indexing = indexing_base_year
            indexing_base_year = 1976
            if avg_monthly_wage >= 1176 and avg_monthly_wage <= 1180:
                monthly_benefits = 557.4
            elif avg_monthly_wage >= 1181 and avg_monthly_wage <= 1185:
                monthly_benefits = 558.4
            elif avg_monthly_wage >= 1186 and avg_monthly_wage <= 1190:
                monthly_benefits = 559.5
            elif avg_monthly_wage >= 1191 and avg_monthly_wage <= 1195:
                monthly_benefits = 560.6
            elif avg_monthly_wage >= 1196 and avg_monthly_wage <= 1200:
                monthly_benefits = 561.6
            elif avg_monthly_wage >= 1201 and avg_monthly_wage <= 1205:
                monthly_benefits = 562.7
            elif avg_monthly_wage >= 1206 and avg_monthly_wage <= 1210:
                monthly_benefits = 563.8
            elif avg_monthly_wage >= 1211 and avg_monthly_wage <= 1215:
                monthly_benefits = 564.8
            elif avg_monthly_wage >= 1216 and avg_monthly_wage <= 1220:
                monthly_benefits = 565.9
            elif avg_monthly_wage >= 1221 and avg_monthly_wage <= 1225:
                monthly_benefits = 566.9
            elif avg_monthly_wage >= 1226 and avg_monthly_wage <= 1230:
                monthly_benefits = 568
            elif avg_monthly_wage >= 1231 and avg_monthly_wage <= 1235:
                monthly_benefits = 569.1
            elif avg_monthly_wage >= 1236 and avg_monthly_wage <= 1240:
                monthly_benefits = 570.1
            elif avg_monthly_wage >= 1241 and avg_monthly_wage <= 1245:
                monthly_benefits = 571.2
            elif avg_monthly_wage >= 1246 and avg_monthly_wage <= 1250:
                monthly_benefits = 572.3
            elif avg_monthly_wage >= 1251 and avg_monthly_wage <= 1255:
                monthly_benefits = 573.3
            elif avg_monthly_wage >= 1256 and avg_monthly_wage <= 1260:
                monthly_benefits = 574.4
            elif avg_monthly_wage >= 1261 and avg_monthly_wage <= 1265:
                monthly_benefits = 575.5
            elif avg_monthly_wage >= 1266 and avg_monthly_wage <= 1270:
                monthly_benefits = 576.5
            elif avg_monthly_wage >= 1271:# and avg_monthly_wage <= 1275:
                monthly_benefits = 577.6
            else: indexing_base_year = old_indexing
        if retirement_year >= 1977:
            old_indexing = indexing_base_year
            indexing_base_year = 1977
            if avg_monthly_wage >= 1276 and avg_monthly_wage <= 1280:
                monthly_benefits = 612.8
            elif avg_monthly_wage >= 1281 and avg_monthly_wage <= 1285:
                monthly_benefits = 613.8
            elif avg_monthly_wage >= 1286 and avg_monthly_wage <= 1290:
                monthly_benefits = 614.9
            elif avg_monthly_wage >= 1291 and avg_monthly_wage <= 1295:
                monthly_benefits = 616
            elif avg_monthly_wage >= 1296 and avg_monthly_wage <= 1300:
                monthly_benefits = 617
            elif avg_monthly_wage >= 1301 and avg_monthly_wage <= 1305:
                monthly_benefits = 618.1
            elif avg_monthly_wage >= 1306 and avg_monthly_wage <= 1310:
                monthly_benefits = 619.1
            elif avg_monthly_wage >= 1311 and avg_monthly_wage <= 1315:
                monthly_benefits = 620.2
            elif avg_monthly_wage >= 1316 and avg_monthly_wage <= 1320:
                monthly_benefits = 621.3
            elif avg_monthly_wage >= 1321 and avg_monthly_wage <= 1325:
                monthly_benefits = 622.3
            elif avg_monthly_wage >= 1326 and avg_monthly_wage <= 1330:
                monthly_benefits = 623.4
            elif avg_monthly_wage >= 1331 and avg_monthly_wage <= 1335:
                monthly_benefits = 624.4
            elif avg_monthly_wage >= 1336 and avg_monthly_wage <= 1340:
                monthly_benefits = 625.5
            elif avg_monthly_wage >= 1341 and avg_monthly_wage <= 1345:
                monthly_benefits = 626.6
            elif avg_monthly_wage >= 1346 and avg_monthly_wage <= 1350:
                monthly_benefits = 627.6
            elif avg_monthly_wage >= 1351 and avg_monthly_wage <= 1355:
                monthly_benefits = 628.7
            elif avg_monthly_wage >= 1356 and avg_monthly_wage <= 1360:
                monthly_benefits = 629.7
            elif avg_monthly_wage >= 1361 and avg_monthly_wage <= 1365:
                monthly_benefits = 630.8
            elif avg_monthly_wage >= 1366 and avg_monthly_wage <= 1370:
                monthly_benefits = 631.8
            elif avg_monthly_wage >= 1371:# and avg_monthly_wage <= 1375:
                monthly_benefits = 632.9
            else: indexing_base_year = old_indexing
        if retirement_year >= 1978:
            old_indexing = indexing_base_year
            indexing_base_year = 1978
            if avg_monthly_wage >= 1376 and avg_monthly_wage <= 1380:
                monthly_benefits = 675.2
            elif avg_monthly_wage >= 1381 and avg_monthly_wage <= 1385:
                monthly_benefits = 676.2
            elif avg_monthly_wage >= 1386 and avg_monthly_wage <= 1390:
                monthly_benefits = 677.3
            elif avg_monthly_wage >= 1391 and avg_monthly_wage <= 1395:
                monthly_benefits = 678.3
            elif avg_monthly_wage >= 1396 and avg_monthly_wage <= 1400:
                monthly_benefits = 679.4
            elif avg_monthly_wage >= 1401 and avg_monthly_wage <= 1405:
                monthly_benefits = 680.5
            elif avg_monthly_wage >= 1406 and avg_monthly_wage <= 1410:
                monthly_benefits = 681.5
            elif avg_monthly_wage >= 1411 and avg_monthly_wage <= 1415:
                monthly_benefits = 682.6
            elif avg_monthly_wage >= 1416 and avg_monthly_wage <= 1420:
                monthly_benefits = 683.7
            elif avg_monthly_wage >= 1421 and avg_monthly_wage <= 1425:
                monthly_benefits = 684.7
            elif avg_monthly_wage >= 1426 and avg_monthly_wage <= 1430:
                monthly_benefits = 685.8
            elif avg_monthly_wage >= 1431 and avg_monthly_wage <= 1435:
                monthly_benefits = 686.9
            elif avg_monthly_wage >= 1436 and avg_monthly_wage <= 1440:
                monthly_benefits = 687.9
            elif avg_monthly_wage >= 1441 and avg_monthly_wage <= 1445:
                monthly_benefits = 689
            elif avg_monthly_wage >= 1446 and avg_monthly_wage <= 1450:
                monthly_benefits = 690.1
            elif avg_monthly_wage >= 1451 and avg_monthly_wage <= 1455:
                monthly_benefits = 691.1
            elif avg_monthly_wage >= 1456 and avg_monthly_wage <= 1460:
                monthly_benefits = 692.2
            elif avg_monthly_wage >= 1461 and avg_monthly_wage <= 1465:
                monthly_benefits = 693.3
            elif avg_monthly_wage >= 1466 and avg_monthly_wage <= 1470:
                monthly_benefits = 694.3
            elif avg_monthly_wage >= 1471:# and avg_monthly_wage <= 1475:
                monthly_benefits = 695.4
            else: indexing_base_year = old_indexing

        if retirement_year >= 1979:
            old_indexing = indexing_base_year
            boundaries = [[1476.0, 1480.0], [1481.0, 1485.0], [1486.0, 1490.0], [1491.0, 1495.0], [1496.0, 1500.0], [1501.0, 1505.0], [1506.0, 1510.0], [1511.0, 1515.0], [1516.0, 1520.0], [1521.0, 1525.0], [1526.0, 1530.0], [1531.0, 1535.0], [1536.0, 1540.0], [1541.0, 1545.0], [1546.0, 1550.0], [1551.0, 1555.0], [1556.0, 1560.0], [1561.0, 1565.0], [1566.0, 1570.0], [1571.0, 1575.0], [1576.0, 1580.0], [1581.0, 1585.0], [1586.0, 1590.0], [1591.0, 1595.0], [1596.0, 1600.0], [1601.0, 1605.0], [1606.0, 1610.0], [1611.0, 1615.0], [1616.0, 1620.0], [1621.0, 1625.0], [1626.0, 1630.0], [1631.0, 1635.0], [1636.0, 1640.0], [1641.0, 1645.0], [1646.0, 1650.0], [1651.0, 1655.0], [1656.0, 1660.0], [1661.0, 1665.0], [1666.0, 1670.0], [1671.0, 1675.0], [1676.0, 1680.0], [1681.0, 1685.0], [1686.0, 1690.0], [1691.0, 1695.0], [1696.0, 1700.0], [1701.0, 1705.0], [1706.0, 1710.0], [1711.0, 1715.0], [1716.0, 1720.0], [1721.0, 1725.0], [1726.0, 1730.0], [1731.0, 1735.0], [1736.0, 1740.0], [1741.0, 1745.0], [1746.0, 1750.0], [1751.0, 1755.0], [1756.0, 1760.0], [1761.0, 1765.0], [1766.0, 1770.0], [1771.0, 1775.0], [1776.0, 1780.0], [1781.0, 1785.0], [1786.0, 1790.0], [1791.0, 1795.0], [1796.0, 1800.0], [1801.0, 1805.0], [1806.0, 1810.0], [1811.0, 1815.0], [1816.0, 1820.0], [1821.0, 1825.0], [1826.0, 1830.0], [1831.0, 1835.0], [1836.0, 1840.0], [1841.0, 1845.0], [1846.0, 1850.0], [1851.0, 1855.0], [1856.0, 1860.0], [1861.0, 1865.0], [1866.0, 1870.0], [1871.0, 1875.0], [1876.0, 1880.0], [1881.0, 1885.0], [1886.0, 1890.0], [1891.0, 1895.0], [1896.0, 1900.0], [1901.0, 1905.0], [1906.0, 100000000000000]]
            benefits = [765.4, 766.5, 767.6, 768.7, 769.8, 770.9, 772.0, 773.1, 774.2, 775.3, 776.4, 777.5, 778.6, 779.7, 780.8, 781.9, 783.0, 784.1, 785.2, 786.3, 787.4, 788.5, 789.6, 790.7, 791.8, 792.9, 794.0, 795.1, 796.2, 797.3, 798.4, 799.5, 800.6, 801.7, 802.8, 803.9, 805.0, 806.1, 807.2, 808.3, 809.4, 810.5, 811.6, 812.7, 813.7, 814.8, 815.9, 817.0, 818.1, 819.2, 820.3, 821.4, 822.5, 823.6, 824.7, 825.8, 826.9, 828.0, 829.1, 830.2, 831.3, 832.4, 833.5, 834.6, 835.7, 836.8, 837.9, 839.0, 840.1, 841.2, 842.3, 843.4, 844.5, 845.6, 846.7, 847.8, 848.9, 850.0, 851.1, 852.2, 853.3, 854.4, 855.5, 856.6, 857.7, 858.8, 859.9]
            for rowNum in range(len(boundaries)):
                
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1979
                    break
                else:
                    indexing_base_year = old_indexing
        if retirement_year >= 1980:
            old_indexing = indexing_base_year
            boundaries = [[1911.0, 1915.0], [1916.0, 1920.0], [1921.0, 1925.0], [1926.0, 1930.0], [1931.0, 1935.0], [1936.0, 1940.0], [1941.0, 1945.0], [1946.0, 1950.0], [1951.0, 1955.0], [1956.0, 1960.0], [1961.0, 1965.0], [1966.0, 1970.0], [1971.0, 1975.0], [1976.0, 1980.0], [1981.0, 1985.0], [1986.0, 1990.0], [1991.0, 1995.0], [1996.0, 2000.0], [2001.0, 2005.0], [2006.0, 2010.0], [2011.0, 2015.0], [2016.0, 2020.0], [2021.0, 2025.0], [2026.0, 2030.0], [2031.0, 2035.0], [2036.0, 2040.0], [2041.0, 2045.0], [2046.0, 2050.0], [2051.0, 2055.0], [2056.0, 2060.0], [2061.0, 2065.0], [2066.0, 2070.0], [2071.0, 2075.0], [2076.0, 2080.0], [2081.0, 2085.0], [2086.0, 2090.0], [2091.0, 2095.0], [2096.0, 2100.0], [2101.0, 2105.0], [2106.0, 2110.0], [2111.0, 2115.0], [2116.0, 2120.0], [2121.0, 2125.0], [2126.0, 2130.0], [2131.0, 2135.0], [2136.0, 2140.0], [2141.0, 2145.0], [2146.0, 2150.0], [2151.0, 2155.0], [2156.0, 1000000000000]]
            benefits = [984.1, 985.2, 986.3, 987.5, 988.6, 989.8, 990.9, 992.1, 993.2, 994.3, 995.5, 996.6, 997.8, 998.9, 1000.1, 1001.2, 1002.3, 1003.5, 1004.6, 1005.8, 1006.9, 1008.1, 1009.2, 1010.3, 1011.5, 1012.6, 1013.8, 1014.9, 1016.1, 1017.2, 1018.3, 1019.5, 1020.6, 1021.8, 1022.9, 1024.1, 1025.2, 1026.3, 1027.5, 1028.6, 1029.8, 1030.9, 1032.1, 1033.2, 1034.4, 1035.5, 1036.6, 1037.8, 1038.9, 1040.1]
            for rowNum in range(len(boundaries)):
                
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1980
                    break
                else:
                    indexing_base_year = old_indexing
        if retirement_year >= 1981:
            old_indexing = indexing_base_year
            boundaries = [[2161.0, 2165.0], [2166.0, 2170.0], [2171.0, 2175.0], [2176.0, 2180.0], [2181.0, 2185.0], [2186.0, 2190.0], [2191.0, 2195.0], [2196.0, 2200.0], [2201.0, 2205.0], [2206.0, 2210.0], [2211.0, 2215.0], [2216.0, 2220.0], [2221.0, 2225.0], [2226.0, 2230.0], [2231.0, 2235.0], [2236.0, 2240.0], [2241.0, 2245.0], [2246.0, 2250.0], [2251.0, 2255.0], [2256.0, 2260.0], [2261.0, 2265.0], [2266.0, 2270.0], [2271.0, 2275.0], [2276.0, 2280.0], [2281.0, 2285.0], [2286.0, 2290.0], [2291.0, 2295.0], [2296.0, 2300.0], [2301.0, 2305.0], [2306.0, 2310.0], [2311.0, 2315.0], [2316.0, 2320.0], [2321.0, 2325.0], [2326.0, 2330.0], [2331.0, 2335.0], [2336.0, 2340.0], [2341.0, 2345.0], [2346.0, 2350.0], [2351.0, 2355.0], [2356.0, 2360.0], [2361.0, 2365.0], [2366.0, 2370.0], [2371.0, 2375.0], [2376.0, 2380.0], [2381.0, 2385.0], [2386.0, 2390.0], [2391.0, 2395.0], [2396.0, 2400.0], [2401.0, 2405.0], [2406.0, 2410.0], [2411.0, 2415.0], [2416.0, 2420.0], [2421.0, 2425.0], [2426.0, 2430.0], [2431.0, 2435.0], [2436.0, 2440.0], [2441.0, 2445.0], [2446.0, 2450.0], [2451.0, 2455.0], [2456.0, 2460.0], [2461.0, 2465.0], [2466.0, 2470.0], [2471.0, 100000000000]]
            benefits = [1157.8, 1158.9, 1160.0, 1161.1, 1162.2, 1163.3, 1164.4, 1165.5, 1166.6, 1167.8, 1168.9, 1170.0, 1171.1, 1172.2, 1173.3, 1174.4, 1175.5, 1176.7, 1177.8, 1178.9, 1180.0, 1181.1, 1182.2, 1183.3, 1184.4, 1185.6, 1186.7, 1187.8, 1188.9, 1190.0, 1191.1, 1192.2, 1193.3, 1194.4, 1195.6, 1196.7, 1197.8, 1198.9, 1200.0, 1201.1, 1202.2, 1203.3, 1204.5, 1205.6, 1206.7, 1207.8, 1208.9, 1210.0, 1211.1, 1212.2, 1213.4, 1214.5, 1215.6, 1216.7, 1217.8, 1218.9, 1220.0, 1221.1, 1222.2, 1223.4, 1224.5, 1225.6, 1226.7]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1981
                    break
                else:
                    indexing_base_year = old_indexing
        if retirement_year >= 1982:
            old_indexing = indexing_base_year
            boundaries = [[2476.0, 2480.0], [2481.0, 2485.0], [2486.0, 2490.0], [2491.0, 2495.0], [2496.0, 2500.0], [2501.0, 2505.0], [2506.0, 2510.0], [2511.0, 2515.0], [2516.0, 2520.0], [2521.0, 2525.0], [2526.0, 2530.0], [2531.0, 2535.0], [2536.0, 2540.0], [2541.0, 2545.0], [2546.0, 2550.0], [2551.0, 2555.0], [2556.0, 2560.0], [2561.0, 2565.0], [2566.0, 2570.0], [2571.0, 2575.0], [2576.0, 2580.0], [2581.0, 2585.0], [2586.0, 2590.0], [2591.0, 2595.0], [2596.0, 2600.0], [2601.0, 2605.0], [2606.0, 2610.0], [2611.0, 2615.0], [2616.0, 2620.0], [2621.0, 2625.0], [2626.0, 2630.0], [2631.0, 2635.0], [2636.0, 2640.0], [2641.0, 2645.0], [2646.0, 2650.0], [2651.0, 2655.0], [2656.0, 2660.0], [2661.0, 2665.0], [2666.0, 2670.0], [2671.0, 2675.0], [2676.0, 2680.0], [2681.0, 2685.0], [2686.0, 2690.0], [2691.0, 2695.0], [2696.0, 100000000000]]
            benefits = [1318.5, 1319.6, 1320.6, 1321.7, 1322.8, 1323.9, 1324.9, 1326.0, 1327.1, 1328.2, 1329.2, 1330.3, 1331.4, 1332.5, 1333.5, 1334.6, 1335.7, 1336.8, 1337.8, 1338.9, 1340.0, 1341.1, 1342.1, 1343.2, 1344.3, 1345.3, 1346.4, 1347.5, 1348.6, 1349.6, 1350.7, 1351.8, 1352.9, 1353.9, 1355.0, 1356.1, 1357.2, 1358.2, 1359.3, 1360.4, 1361.5, 1362.5, 1363.6, 1364.7, 1365.8]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1982
                    break
                else:
                    indexing_base_year = old_indexing
        
        if retirement_year >= 1983:
            old_indexing = indexing_base_year
            boundaries = [[2706.0, 2710.0], [2711.0, 2715.0], [2716.0, 2720.0], [2721.0, 2725.0], [2726.0, 2730.0], [2731.0, 2735.0], [2736.0, 2740.0], [2741.0, 2745.0], [2746.0, 2750.0], [2751.0, 2755.0], [2756.0, 2760.0], [2761.0, 2765.0], [2766.0, 2770.0], [2771.0, 2775.0], [2776.0, 2780.0], [2781.0, 2785.0], [2786.0, 2790.0], [2791.0, 2795.0], [2796.0, 2800.0], [2801.0, 2805.0], [2806.0, 2810.0], [2811.0, 2815.0], [2816.0, 2820.0], [2821.0, 2825.0], [2826.0, 2830.0], [2831.0, 2835.0], [2836.0, 2840.0], [2841.0, 2845.0], [2846.0, 2850.0], [2851.0, 2855.0], [2856.0, 2860.0], [2861.0, 2865.0], [2866.0, 2870.0], [2871.0, 2875.0], [2876.0, 2880.0], [2881.0, 2885.0], [2886.0, 2890.0], [2891.0, 2895.0], [2896.0, 2900.0], [2901.0, 2905.0], [2906.0, 2910.0], [2911.0, 2915.0], [2916.0, 2920.0], [2921.0, 2925.0], [2926.0, 2930.0], [2931.0, 2935.0], [2936.0, 2940.0], [2941.0, 2945.0], [2946.0, 2950.0], [2951.0, 2955.0], [2956.0, 2960.0], [2961.0, 2965.0], [2966.0, 2970.0], [2971.0, 100000000000000]]
            benefits = [1415.6, 1416.7, 1417.7, 1418.7, 1419.8, 1420.8, 1421.8, 1422.9, 1423.9, 1424.9, 1426.0, 1427.0, 1428.0, 1429.1, 1430.1, 1431.1, 1432.2, 1433.2, 1434.3, 1435.3, 1436.3, 1437.4, 1438.4, 1439.4, 1440.5, 1441.5, 1442.5, 1443.6, 1444.6, 1445.6, 1446.7, 1447.7, 1448.7, 1449.8, 1450.8, 1451.8, 1452.9, 1453.9, 1455.0, 1456.0, 1457.0, 1458.1, 1459.1, 1460.1, 1461.2, 1462.2, 1463.2, 1464.3, 1465.3, 1466.3, 1467.4, 1468.4, 1469.4, 1470.5]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1983
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1984:
            old_indexing = indexing_base_year
            boundaries = [[2976.0, 2980.0], [2981.0, 2985.0], [2986.0, 2990.0], [2991.0, 2995.0], [2996.0, 3000.0], [3001.0, 3005.0], [3006.0, 3010.0], [3011.0, 3015.0], [3016.0, 3020.0], [3021.0, 3025.0], [3026.0, 3030.0], [3031.0, 3035.0], [3036.0, 3040.0], [3041.0, 3045.0], [3046.0, 3050.0], [3051.0, 3055.0], [3056.0, 3060.0], [3061.0, 3065.0], [3066.0, 3070.0], [3071.0, 3075.0], [3076.0, 3080.0], [3081.0, 3085.0], [3086.0, 3090.0], [3091.0, 3095.0], [3096.0, 3100.0], [3101.0, 3105.0], [3106.0, 3110.0], [3111.0, 3115.0], [3116.0, 3120.0], [3121.0, 3125.0], [3126.0, 3130.0], [3131.0, 3135.0], [3136.0, 3140.0], [3141.0, 3145.0], [3146.0, 10000000000000000]]
            benefits = [1523.0, 1524.0, 1525.0, 1526.1, 1527.1, 1528.1, 1529.2, 1530.2, 1531.2, 1532.3, 1533.3, 1534.3, 1535.4, 1536.4, 1537.4, 1538.5, 1539.5, 1540.5, 1541.6, 1542.6, 1543.7, 1544.7, 1545.7, 1546.8, 1547.8, 1548.8, 1549.9, 1550.9, 1551.9, 1553.0, 1554.0, 1555.0, 1556.1, 1557.1, 1558.1]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1984
                    break
                else:
                    indexing_base_year = old_indexing
        
        if retirement_year >= 1985:
            old_indexing = indexing_base_year
            boundaries = [[3156.0, 3160.0], [3161.0, 3165.0], [3166.0, 3170.0], [3171.0, 3175.0], [3176.0, 3180.0], [3181.0, 3185.0], [3186.0, 3190.0], [3191.0, 3195.0], [3196.0, 3200.0], [3201.0, 3205.0], [3206.0, 3210.0], [3211.0, 3215.0], [3216.0, 3220.0], [3221.0, 3225.0], [3226.0, 3230.0], [3231.0, 3235.0], [3236.0, 3240.0], [3241.0, 3245.0], [3246.0, 3250.0], [3251.0, 3255.0], [3256.0, 3260.0], [3261.0, 3265.0], [3266.0, 3270.0], [3271.0, 3275.0], [3276.0, 3280.0], [3281.0, 3285.0], [3286.0, 3290.0], [3291.0, 3295.0], [3296.0, 10000000000000000]]
            benefits = [1608.4, 1609.4, 1610.5, 1611.5, 1612.5, 1613.6, 1614.6, 1615.6, 1616.7, 1617.7, 1618.7, 1619.8, 1620.8, 1621.8, 1622.8, 1623.9, 1624.9, 1625.9, 1627.0, 1628.0, 1629.0, 1630.1, 1631.1, 1632.1, 1633.2, 1634.2, 1635.2, 1636.3, 1637.3]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1985
                    break
                else:
                    indexing_base_year = old_indexing
        
        if retirement_year >= 1986:
            old_indexing = indexing_base_year
            boundaries = [[3306.0, 3310.0], [3311.0, 3315.0], [3316.0, 3320.0], [3321.0, 3325.0], [3326.0, 3330.0], [3331.0, 3335.0], [3336.0, 3340.0], [3341.0, 3345.0], [3346.0, 3350.0], [3351.0, 3355.0], [3356.0, 3360.0], [3361.0, 3365.0], [3366.0, 3370.0], [3371.0, 3375.0], [3376.0, 3380.0], [3381.0, 3385.0], [3386.0, 3390.0], [3391.0, 3395.0], [3396.0, 3400.0], [3401.0, 3405.0], [3406.0, 3410.0], [3411.0, 3415.0], [3416.0, 3420.0], [3421.0, 3425.0], [3426.0, 3430.0], [3431.0, 3435.0], [3436.0, 3440.0], [3441.0, 3445.0], [3446.0, 3450.0], [3451.0, 3455.0], [3456.0, 3460.0], [3461.0, 3465.0], [3466.0, 3470.0], [3471.0, 3475.0], [3476.0, 3480.0], [3481.0, 3485.0], [3486.0, 3490.0], [3491.0, 3495.0], [3496.0, 10000000000000000]]
            benefits = [1660.6, 1661.6, 1662.6, 1663.6, 1664.6, 1665.6, 1666.6, 1667.7, 1668.7, 1669.7, 1670.7, 1671.7, 1672.7, 1673.7, 1674.7, 1675.8, 1676.8, 1677.8, 1678.8, 1679.8, 1680.8, 1681.8, 1682.8, 1683.9, 1684.9, 1685.9, 1686.9, 1687.9, 1688.9, 1689.9, 1691.0, 1692.0, 1693.0, 1694.0, 1695.0, 1696.0, 1697.0, 1698.0, 1699.1]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1986
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1987:
            old_indexing = indexing_base_year
            boundaries =[[3506.0, 3510.0], [3511.0, 3515.0], [3516.0, 3520.0], [3521.0, 3525.0], [3526.0, 3530.0], [3531.0, 3535.0], [3536.0, 3540.0], [3541.0, 3545.0], [3546.0, 3550.0], [3551.0, 3555.0], [3556.0, 3560.0], [3561.0, 3565.0], [3566.0, 3570.0], [3571.0, 3575.0], [3576.0, 3580.0], [3581.0, 3585.0], [3586.0, 3590.0], [3591.0, 3595.0], [3596.0, 3600.0], [3601.0, 3605.0], [3606.0, 3610.0], [3611.0, 3615.0], [3616.0, 3620.0], [3621.0, 3625.0], [3626.0, 3630.0], [3631.0, 3635.0], [3636.0, 3640.0], [3641.0, 3645.0], [3646.0, 1000000000000000]]
            benefits = [1772.5, 1773.5, 1774.6, 1775.6, 1776.7, 1777.7, 1778.7, 1779.8, 1780.8, 1781.9, 1782.9, 1784.0, 1785.0, 1786.0, 1787.1, 1788.1, 1789.2, 1790.2, 1791.3, 1792.3, 1793.3, 1794.4, 1795.4, 1796.5, 1797.5, 1798.5, 1799.6, 1800.6, 1801.7]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1987
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1988:
            old_indexing = indexing_base_year
            boundaries =[[3656.0, 3660.0], [3661.0, 3665.0], [3666.0, 3670.0], [3671.0, 3675.0], [3676.0, 3680.0], [3681.0, 3685.0], [3686.0, 3690.0], [3691.0, 3695.0], [3696.0, 3700.0], [3701.0, 3705.0], [3706.0, 3710.0], [3711.0, 3715.0], [3716.0, 3720.0], [3721.0, 3725.0], [3726.0, 3730.0], [3731.0, 3735.0], [3736.0, 3740.0], [3741.0, 3745.0], [3746.0, 1000000000000000000]]
            benefits = [1875.8, 1876.8, 1877.9, 1878.9, 1880.0, 1881.0, 1882.0, 1883.1, 1884.1, 1885.2, 1886.2, 1887.2, 1888.3, 1889.3, 1890.4, 1891.4, 1892.4, 1893.5, 1894.5]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1988
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1989:
            old_indexing = indexing_base_year
            boundaries =[[3756.0, 3760.0], [3761.0, 3765.0], [3766.0, 3770.0], [3771.0, 3775.0], [3776.0, 3780.0], [3781.0, 3785.0], [3786.0, 3790.0], [3791.0, 3795.0], [3796.0, 3800.0], [3801.0, 3805.0], [3806.0, 3810.0], [3811.0, 3815.0], [3816.0, 3820.0], [3821.0, 3825.0], [3826.0, 3830.0], [3831.0, 3835.0], [3836.0, 3840.0], [3841.0, 3845.0], [3846.0, 3850.0], [3851.0, 3855.0], [3856.0, 3860.0], [3861.0, 3865.0], [3866.0, 3870.0], [3871.0, 3875.0], [3876.0, 3880.0], [3881.0, 3885.0], [3886.0, 3890.0], [3891.0, 3895.0], [3896.0, 3900.0], [3901.0, 3905.0], [3906.0, 3910.0], [3911.0, 3915.0], [3916.0, 3920.0], [3921.0, 3925.0], [3926.0, 3930.0], [3931.0, 3935.0], [3936.0, 3940.0], [3941.0, 3945.0], [3946.0, 3950.0], [3951.0, 3955.0], [3956.0, 3960.0], [3961.0, 3965.0], [3966.0, 3970.0], [3971.0, 3975.0], [3976.0, 3980.0], [3981.0, 3985.0], [3986.0, 3990.0], [3991.0, 3995.0], [3996.0, 10000000000000000.0]]
            benefits = [1985.6, 1986.6, 1987.7, 1988.7, 1989.8, 1990.8, 1991.9, 1992.9, 1994.0, 1995.0, 1996.1, 1997.1, 1998.1, 1999.2, 2000.2, 2001.3, 2002.3, 2003.4, 2004.4, 2005.5, 2006.5, 2007.6, 2008.6, 2009.7, 2010.7, 2011.8, 2012.8, 2013.9, 2014.9, 2015.9, 2017.0, 2018.0, 2019.1, 2020.1, 2021.2, 2022.2, 2023.3, 2024.3, 2025.4, 2026.4, 2027.5, 2028.5, 2029.6, 2030.6, 2031.7, 2032.7, 2033.7, 2034.8, 2035.8]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1989
                    break
                else:
                    indexing_base_year = old_indexing
    
    
    #ChatGpt wrote the following block because my code messed up -- DCarrillo
    ###########
    for i in range(indexing_base_year + 1,reference_year):
        #print(i, " applied: ", cola_adjustments[i+1], " and ", indexed_monthly_benefits*(1+cola_adjustments[i+1]))
        cola = (1+cola_adjustments[i+1]) 
        if i == 1999 and retirement_year > 2001: 
            cola = 1.025 #Pursuant to Public Law 106-554
        monthly_benefits*=cola #this is actually not quite right, this smoothes how the adjustments are actually done seen on pages 7 and 8 of pdf, this actually probably produces a positive bias on long time scales of benefits paid outs
    

    if spouse_birth_year + 65 > spouse_retirement_year:
        deduction = deduction - (25/36) * 0.01 * 12 *(spouse_birth_year+65 - spouse_retirement_year)

    #print("postmon: ", monthly_benefits)

    #print("deduct: ", deduction)

    spouse_benefit_guarantee = 0.5*monthly_benefits *deduction

    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    if reference_year >= 1983:
        return math.floor(spousal_benefit)
    elif reference_year >= 1977:
        return math.ceil(spousal_benefit * 10) / 10
    else:
        return math.ceil(10*spousal_benefit) /10 #in 1972, spousal benefits began to increase with COLA. However, if b1972 and bb1972 account for these COLA adjustments, we do not need to account again here.


def tableMaxCalc(primaryPIA, avg, retirement_year:int):
    indexing_base_year = 1974
    avg_monthly_wage = avg
    monthly_benefits = primaryPIA
    if monthly_benefits == 469.00 and retirement_year >= 1975:
        if avg_monthly_wage >= 469:
            if retirement_year >= 1975:
                indexing_base_year = 1975
                if avg_monthly_wage >= 1101 and avg_monthly_wage <= 1105:
                    monthly_benefits = 507.6
                elif avg_monthly_wage >= 1106 and avg_monthly_wage <= 1110:
                    monthly_benefits = 508.7
                elif avg_monthly_wage >= 1111 and avg_monthly_wage <= 1115:
                    monthly_benefits = 509.8
                elif avg_monthly_wage >= 1116 and avg_monthly_wage <= 1120:
                    monthly_benefits = 510.9
                elif avg_monthly_wage >= 1121 and avg_monthly_wage <= 1125:
                    monthly_benefits = 512
                elif avg_monthly_wage >= 1126 and avg_monthly_wage <= 1130:
                    monthly_benefits = 513
                elif avg_monthly_wage >= 1131 and avg_monthly_wage <= 1135:
                    monthly_benefits = 514.1
                elif avg_monthly_wage >= 1136 and avg_monthly_wage <= 1140:
                    monthly_benefits = 515.2
                elif avg_monthly_wage >= 1141 and avg_monthly_wage <= 1145:
                    monthly_benefits = 516.3
                elif avg_monthly_wage >= 1146 and avg_monthly_wage <= 1150:
                    monthly_benefits = 517.4
                elif avg_monthly_wage >= 1151 and avg_monthly_wage <= 1155:
                    monthly_benefits = 518.4
                elif avg_monthly_wage >= 1156 and avg_monthly_wage <= 1160:
                    monthly_benefits = 519.5
                elif avg_monthly_wage >= 1161 and avg_monthly_wage <= 1165:
                    monthly_benefits = 520.6
                elif avg_monthly_wage >= 1166 and avg_monthly_wage <= 1170:
                    monthly_benefits = 521.7
                elif avg_monthly_wage >= 1171: #and avg_monthly_wage <= 1175:
                    monthly_benefits = 522.8
                else: indexing_base_year = 1974
                
        if retirement_year >= 1976:
            #print("hello! ", avg_monthly_wage)
            old_indexing = indexing_base_year
            indexing_base_year = 1976
            if avg_monthly_wage >= 1176 and avg_monthly_wage <= 1180:
                monthly_benefits = 557.4
            elif avg_monthly_wage >= 1181 and avg_monthly_wage <= 1185:
                monthly_benefits = 558.4
            elif avg_monthly_wage >= 1186 and avg_monthly_wage <= 1190:
                monthly_benefits = 559.5
            elif avg_monthly_wage >= 1191 and avg_monthly_wage <= 1195:
                monthly_benefits = 560.6
            elif avg_monthly_wage >= 1196 and avg_monthly_wage <= 1200:
                monthly_benefits = 561.6
            elif avg_monthly_wage >= 1201 and avg_monthly_wage <= 1205:
                monthly_benefits = 562.7
            elif avg_monthly_wage >= 1206 and avg_monthly_wage <= 1210:
                monthly_benefits = 563.8
            elif avg_monthly_wage >= 1211 and avg_monthly_wage <= 1215:
                monthly_benefits = 564.8
            elif avg_monthly_wage >= 1216 and avg_monthly_wage <= 1220:
                monthly_benefits = 565.9
            elif avg_monthly_wage >= 1221 and avg_monthly_wage <= 1225:
                monthly_benefits = 566.9
            elif avg_monthly_wage >= 1226 and avg_monthly_wage <= 1230:
                monthly_benefits = 568
            elif avg_monthly_wage >= 1231 and avg_monthly_wage <= 1235:
                monthly_benefits = 569.1
            elif avg_monthly_wage >= 1236 and avg_monthly_wage <= 1240:
                monthly_benefits = 570.1
            elif avg_monthly_wage >= 1241 and avg_monthly_wage <= 1245:
                monthly_benefits = 571.2
            elif avg_monthly_wage >= 1246 and avg_monthly_wage <= 1250:
                monthly_benefits = 572.3
            elif avg_monthly_wage >= 1251 and avg_monthly_wage <= 1255:
                monthly_benefits = 573.3
            elif avg_monthly_wage >= 1256 and avg_monthly_wage <= 1260:
                monthly_benefits = 574.4
            elif avg_monthly_wage >= 1261 and avg_monthly_wage <= 1265:
                monthly_benefits = 575.5
            elif avg_monthly_wage >= 1266 and avg_monthly_wage <= 1270:
                monthly_benefits = 576.5
            elif avg_monthly_wage >= 1271:# and avg_monthly_wage <= 1275:
                monthly_benefits = 577.6
            else: indexing_base_year = old_indexing
        if retirement_year >= 1977:
            old_indexing = indexing_base_year
            indexing_base_year = 1977
            if avg_monthly_wage >= 1276 and avg_monthly_wage <= 1280:
                monthly_benefits = 612.8
            elif avg_monthly_wage >= 1281 and avg_monthly_wage <= 1285:
                monthly_benefits = 613.8
            elif avg_monthly_wage >= 1286 and avg_monthly_wage <= 1290:
                monthly_benefits = 614.9
            elif avg_monthly_wage >= 1291 and avg_monthly_wage <= 1295:
                monthly_benefits = 616
            elif avg_monthly_wage >= 1296 and avg_monthly_wage <= 1300:
                monthly_benefits = 617
            elif avg_monthly_wage >= 1301 and avg_monthly_wage <= 1305:
                monthly_benefits = 618.1
            elif avg_monthly_wage >= 1306 and avg_monthly_wage <= 1310:
                monthly_benefits = 619.1
            elif avg_monthly_wage >= 1311 and avg_monthly_wage <= 1315:
                monthly_benefits = 620.2
            elif avg_monthly_wage >= 1316 and avg_monthly_wage <= 1320:
                monthly_benefits = 621.3
            elif avg_monthly_wage >= 1321 and avg_monthly_wage <= 1325:
                monthly_benefits = 622.3
            elif avg_monthly_wage >= 1326 and avg_monthly_wage <= 1330:
                monthly_benefits = 623.4
            elif avg_monthly_wage >= 1331 and avg_monthly_wage <= 1335:
                monthly_benefits = 624.4
            elif avg_monthly_wage >= 1336 and avg_monthly_wage <= 1340:
                monthly_benefits = 625.5
            elif avg_monthly_wage >= 1341 and avg_monthly_wage <= 1345:
                monthly_benefits = 626.6
            elif avg_monthly_wage >= 1346 and avg_monthly_wage <= 1350:
                monthly_benefits = 627.6
            elif avg_monthly_wage >= 1351 and avg_monthly_wage <= 1355:
                monthly_benefits = 628.7
            elif avg_monthly_wage >= 1356 and avg_monthly_wage <= 1360:
                monthly_benefits = 629.7
            elif avg_monthly_wage >= 1361 and avg_monthly_wage <= 1365:
                monthly_benefits = 630.8
            elif avg_monthly_wage >= 1366 and avg_monthly_wage <= 1370:
                monthly_benefits = 631.8
            elif avg_monthly_wage >= 1371:# and avg_monthly_wage <= 1375:
                monthly_benefits = 632.9
            else: indexing_base_year = old_indexing
        if retirement_year >= 1978:
            old_indexing = indexing_base_year
            indexing_base_year = 1978
            if avg_monthly_wage >= 1376 and avg_monthly_wage <= 1380:
                monthly_benefits = 675.2
            elif avg_monthly_wage >= 1381 and avg_monthly_wage <= 1385:
                monthly_benefits = 676.2
            elif avg_monthly_wage >= 1386 and avg_monthly_wage <= 1390:
                monthly_benefits = 677.3
            elif avg_monthly_wage >= 1391 and avg_monthly_wage <= 1395:
                monthly_benefits = 678.3
            elif avg_monthly_wage >= 1396 and avg_monthly_wage <= 1400:
                monthly_benefits = 679.4
            elif avg_monthly_wage >= 1401 and avg_monthly_wage <= 1405:
                monthly_benefits = 680.5
            elif avg_monthly_wage >= 1406 and avg_monthly_wage <= 1410:
                monthly_benefits = 681.5
            elif avg_monthly_wage >= 1411 and avg_monthly_wage <= 1415:
                monthly_benefits = 682.6
            elif avg_monthly_wage >= 1416 and avg_monthly_wage <= 1420:
                monthly_benefits = 683.7
            elif avg_monthly_wage >= 1421 and avg_monthly_wage <= 1425:
                monthly_benefits = 684.7
            elif avg_monthly_wage >= 1426 and avg_monthly_wage <= 1430:
                monthly_benefits = 685.8
            elif avg_monthly_wage >= 1431 and avg_monthly_wage <= 1435:
                monthly_benefits = 686.9
            elif avg_monthly_wage >= 1436 and avg_monthly_wage <= 1440:
                monthly_benefits = 687.9
            elif avg_monthly_wage >= 1441 and avg_monthly_wage <= 1445:
                monthly_benefits = 689
            elif avg_monthly_wage >= 1446 and avg_monthly_wage <= 1450:
                monthly_benefits = 690.1
            elif avg_monthly_wage >= 1451 and avg_monthly_wage <= 1455:
                monthly_benefits = 691.1
            elif avg_monthly_wage >= 1456 and avg_monthly_wage <= 1460:
                monthly_benefits = 692.2
            elif avg_monthly_wage >= 1461 and avg_monthly_wage <= 1465:
                monthly_benefits = 693.3
            elif avg_monthly_wage >= 1466 and avg_monthly_wage <= 1470:
                monthly_benefits = 694.3
            elif avg_monthly_wage >= 1471:# and avg_monthly_wage <= 1475:
                monthly_benefits = 695.4
            else: indexing_base_year = old_indexing

        if retirement_year >= 1979:
            old_indexing = indexing_base_year
            boundaries = [[1476.0, 1480.0], [1481.0, 1485.0], [1486.0, 1490.0], [1491.0, 1495.0], [1496.0, 1500.0], [1501.0, 1505.0], [1506.0, 1510.0], [1511.0, 1515.0], [1516.0, 1520.0], [1521.0, 1525.0], [1526.0, 1530.0], [1531.0, 1535.0], [1536.0, 1540.0], [1541.0, 1545.0], [1546.0, 1550.0], [1551.0, 1555.0], [1556.0, 1560.0], [1561.0, 1565.0], [1566.0, 1570.0], [1571.0, 1575.0], [1576.0, 1580.0], [1581.0, 1585.0], [1586.0, 1590.0], [1591.0, 1595.0], [1596.0, 1600.0], [1601.0, 1605.0], [1606.0, 1610.0], [1611.0, 1615.0], [1616.0, 1620.0], [1621.0, 1625.0], [1626.0, 1630.0], [1631.0, 1635.0], [1636.0, 1640.0], [1641.0, 1645.0], [1646.0, 1650.0], [1651.0, 1655.0], [1656.0, 1660.0], [1661.0, 1665.0], [1666.0, 1670.0], [1671.0, 1675.0], [1676.0, 1680.0], [1681.0, 1685.0], [1686.0, 1690.0], [1691.0, 1695.0], [1696.0, 1700.0], [1701.0, 1705.0], [1706.0, 1710.0], [1711.0, 1715.0], [1716.0, 1720.0], [1721.0, 1725.0], [1726.0, 1730.0], [1731.0, 1735.0], [1736.0, 1740.0], [1741.0, 1745.0], [1746.0, 1750.0], [1751.0, 1755.0], [1756.0, 1760.0], [1761.0, 1765.0], [1766.0, 1770.0], [1771.0, 1775.0], [1776.0, 1780.0], [1781.0, 1785.0], [1786.0, 1790.0], [1791.0, 1795.0], [1796.0, 1800.0], [1801.0, 1805.0], [1806.0, 1810.0], [1811.0, 1815.0], [1816.0, 1820.0], [1821.0, 1825.0], [1826.0, 1830.0], [1831.0, 1835.0], [1836.0, 1840.0], [1841.0, 1845.0], [1846.0, 1850.0], [1851.0, 1855.0], [1856.0, 1860.0], [1861.0, 1865.0], [1866.0, 1870.0], [1871.0, 1875.0], [1876.0, 1880.0], [1881.0, 1885.0], [1886.0, 1890.0], [1891.0, 1895.0], [1896.0, 1900.0], [1901.0, 1905.0], [1906.0, 100000000000000]]
            benefits = [765.4, 766.5, 767.6, 768.7, 769.8, 770.9, 772.0, 773.1, 774.2, 775.3, 776.4, 777.5, 778.6, 779.7, 780.8, 781.9, 783.0, 784.1, 785.2, 786.3, 787.4, 788.5, 789.6, 790.7, 791.8, 792.9, 794.0, 795.1, 796.2, 797.3, 798.4, 799.5, 800.6, 801.7, 802.8, 803.9, 805.0, 806.1, 807.2, 808.3, 809.4, 810.5, 811.6, 812.7, 813.7, 814.8, 815.9, 817.0, 818.1, 819.2, 820.3, 821.4, 822.5, 823.6, 824.7, 825.8, 826.9, 828.0, 829.1, 830.2, 831.3, 832.4, 833.5, 834.6, 835.7, 836.8, 837.9, 839.0, 840.1, 841.2, 842.3, 843.4, 844.5, 845.6, 846.7, 847.8, 848.9, 850.0, 851.1, 852.2, 853.3, 854.4, 855.5, 856.6, 857.7, 858.8, 859.9]
            for rowNum in range(len(boundaries)):
                
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1979
                    break
                else:
                    indexing_base_year = old_indexing
        if retirement_year >= 1980:
            old_indexing = indexing_base_year
            boundaries = [[1911.0, 1915.0], [1916.0, 1920.0], [1921.0, 1925.0], [1926.0, 1930.0], [1931.0, 1935.0], [1936.0, 1940.0], [1941.0, 1945.0], [1946.0, 1950.0], [1951.0, 1955.0], [1956.0, 1960.0], [1961.0, 1965.0], [1966.0, 1970.0], [1971.0, 1975.0], [1976.0, 1980.0], [1981.0, 1985.0], [1986.0, 1990.0], [1991.0, 1995.0], [1996.0, 2000.0], [2001.0, 2005.0], [2006.0, 2010.0], [2011.0, 2015.0], [2016.0, 2020.0], [2021.0, 2025.0], [2026.0, 2030.0], [2031.0, 2035.0], [2036.0, 2040.0], [2041.0, 2045.0], [2046.0, 2050.0], [2051.0, 2055.0], [2056.0, 2060.0], [2061.0, 2065.0], [2066.0, 2070.0], [2071.0, 2075.0], [2076.0, 2080.0], [2081.0, 2085.0], [2086.0, 2090.0], [2091.0, 2095.0], [2096.0, 2100.0], [2101.0, 2105.0], [2106.0, 2110.0], [2111.0, 2115.0], [2116.0, 2120.0], [2121.0, 2125.0], [2126.0, 2130.0], [2131.0, 2135.0], [2136.0, 2140.0], [2141.0, 2145.0], [2146.0, 2150.0], [2151.0, 2155.0], [2156.0, 1000000000000]]
            benefits = [984.1, 985.2, 986.3, 987.5, 988.6, 989.8, 990.9, 992.1, 993.2, 994.3, 995.5, 996.6, 997.8, 998.9, 1000.1, 1001.2, 1002.3, 1003.5, 1004.6, 1005.8, 1006.9, 1008.1, 1009.2, 1010.3, 1011.5, 1012.6, 1013.8, 1014.9, 1016.1, 1017.2, 1018.3, 1019.5, 1020.6, 1021.8, 1022.9, 1024.1, 1025.2, 1026.3, 1027.5, 1028.6, 1029.8, 1030.9, 1032.1, 1033.2, 1034.4, 1035.5, 1036.6, 1037.8, 1038.9, 1040.1]
            for rowNum in range(len(boundaries)):
                
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1980
                    break
                else:
                    indexing_base_year = old_indexing
        if retirement_year >= 1981:
            old_indexing = indexing_base_year
            boundaries = [[2161.0, 2165.0], [2166.0, 2170.0], [2171.0, 2175.0], [2176.0, 2180.0], [2181.0, 2185.0], [2186.0, 2190.0], [2191.0, 2195.0], [2196.0, 2200.0], [2201.0, 2205.0], [2206.0, 2210.0], [2211.0, 2215.0], [2216.0, 2220.0], [2221.0, 2225.0], [2226.0, 2230.0], [2231.0, 2235.0], [2236.0, 2240.0], [2241.0, 2245.0], [2246.0, 2250.0], [2251.0, 2255.0], [2256.0, 2260.0], [2261.0, 2265.0], [2266.0, 2270.0], [2271.0, 2275.0], [2276.0, 2280.0], [2281.0, 2285.0], [2286.0, 2290.0], [2291.0, 2295.0], [2296.0, 2300.0], [2301.0, 2305.0], [2306.0, 2310.0], [2311.0, 2315.0], [2316.0, 2320.0], [2321.0, 2325.0], [2326.0, 2330.0], [2331.0, 2335.0], [2336.0, 2340.0], [2341.0, 2345.0], [2346.0, 2350.0], [2351.0, 2355.0], [2356.0, 2360.0], [2361.0, 2365.0], [2366.0, 2370.0], [2371.0, 2375.0], [2376.0, 2380.0], [2381.0, 2385.0], [2386.0, 2390.0], [2391.0, 2395.0], [2396.0, 2400.0], [2401.0, 2405.0], [2406.0, 2410.0], [2411.0, 2415.0], [2416.0, 2420.0], [2421.0, 2425.0], [2426.0, 2430.0], [2431.0, 2435.0], [2436.0, 2440.0], [2441.0, 2445.0], [2446.0, 2450.0], [2451.0, 2455.0], [2456.0, 2460.0], [2461.0, 2465.0], [2466.0, 2470.0], [2471.0, 100000000000]]
            benefits = [1157.8, 1158.9, 1160.0, 1161.1, 1162.2, 1163.3, 1164.4, 1165.5, 1166.6, 1167.8, 1168.9, 1170.0, 1171.1, 1172.2, 1173.3, 1174.4, 1175.5, 1176.7, 1177.8, 1178.9, 1180.0, 1181.1, 1182.2, 1183.3, 1184.4, 1185.6, 1186.7, 1187.8, 1188.9, 1190.0, 1191.1, 1192.2, 1193.3, 1194.4, 1195.6, 1196.7, 1197.8, 1198.9, 1200.0, 1201.1, 1202.2, 1203.3, 1204.5, 1205.6, 1206.7, 1207.8, 1208.9, 1210.0, 1211.1, 1212.2, 1213.4, 1214.5, 1215.6, 1216.7, 1217.8, 1218.9, 1220.0, 1221.1, 1222.2, 1223.4, 1224.5, 1225.6, 1226.7]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1981
                    break
                else:
                    indexing_base_year = old_indexing
        if retirement_year >= 1982:
            old_indexing = indexing_base_year
            boundaries = [[2476.0, 2480.0], [2481.0, 2485.0], [2486.0, 2490.0], [2491.0, 2495.0], [2496.0, 2500.0], [2501.0, 2505.0], [2506.0, 2510.0], [2511.0, 2515.0], [2516.0, 2520.0], [2521.0, 2525.0], [2526.0, 2530.0], [2531.0, 2535.0], [2536.0, 2540.0], [2541.0, 2545.0], [2546.0, 2550.0], [2551.0, 2555.0], [2556.0, 2560.0], [2561.0, 2565.0], [2566.0, 2570.0], [2571.0, 2575.0], [2576.0, 2580.0], [2581.0, 2585.0], [2586.0, 2590.0], [2591.0, 2595.0], [2596.0, 2600.0], [2601.0, 2605.0], [2606.0, 2610.0], [2611.0, 2615.0], [2616.0, 2620.0], [2621.0, 2625.0], [2626.0, 2630.0], [2631.0, 2635.0], [2636.0, 2640.0], [2641.0, 2645.0], [2646.0, 2650.0], [2651.0, 2655.0], [2656.0, 2660.0], [2661.0, 2665.0], [2666.0, 2670.0], [2671.0, 2675.0], [2676.0, 2680.0], [2681.0, 2685.0], [2686.0, 2690.0], [2691.0, 2695.0], [2696.0, 100000000000]]
            benefits = [1318.5, 1319.6, 1320.6, 1321.7, 1322.8, 1323.9, 1324.9, 1326.0, 1327.1, 1328.2, 1329.2, 1330.3, 1331.4, 1332.5, 1333.5, 1334.6, 1335.7, 1336.8, 1337.8, 1338.9, 1340.0, 1341.1, 1342.1, 1343.2, 1344.3, 1345.3, 1346.4, 1347.5, 1348.6, 1349.6, 1350.7, 1351.8, 1352.9, 1353.9, 1355.0, 1356.1, 1357.2, 1358.2, 1359.3, 1360.4, 1361.5, 1362.5, 1363.6, 1364.7, 1365.8]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1982
                    break
                else:
                    indexing_base_year = old_indexing
        
        if retirement_year >= 1983:
            old_indexing = indexing_base_year
            boundaries = [[2706.0, 2710.0], [2711.0, 2715.0], [2716.0, 2720.0], [2721.0, 2725.0], [2726.0, 2730.0], [2731.0, 2735.0], [2736.0, 2740.0], [2741.0, 2745.0], [2746.0, 2750.0], [2751.0, 2755.0], [2756.0, 2760.0], [2761.0, 2765.0], [2766.0, 2770.0], [2771.0, 2775.0], [2776.0, 2780.0], [2781.0, 2785.0], [2786.0, 2790.0], [2791.0, 2795.0], [2796.0, 2800.0], [2801.0, 2805.0], [2806.0, 2810.0], [2811.0, 2815.0], [2816.0, 2820.0], [2821.0, 2825.0], [2826.0, 2830.0], [2831.0, 2835.0], [2836.0, 2840.0], [2841.0, 2845.0], [2846.0, 2850.0], [2851.0, 2855.0], [2856.0, 2860.0], [2861.0, 2865.0], [2866.0, 2870.0], [2871.0, 2875.0], [2876.0, 2880.0], [2881.0, 2885.0], [2886.0, 2890.0], [2891.0, 2895.0], [2896.0, 2900.0], [2901.0, 2905.0], [2906.0, 2910.0], [2911.0, 2915.0], [2916.0, 2920.0], [2921.0, 2925.0], [2926.0, 2930.0], [2931.0, 2935.0], [2936.0, 2940.0], [2941.0, 2945.0], [2946.0, 2950.0], [2951.0, 2955.0], [2956.0, 2960.0], [2961.0, 2965.0], [2966.0, 2970.0], [2971.0, 100000000000000]]
            benefits = [1415.6, 1416.7, 1417.7, 1418.7, 1419.8, 1420.8, 1421.8, 1422.9, 1423.9, 1424.9, 1426.0, 1427.0, 1428.0, 1429.1, 1430.1, 1431.1, 1432.2, 1433.2, 1434.3, 1435.3, 1436.3, 1437.4, 1438.4, 1439.4, 1440.5, 1441.5, 1442.5, 1443.6, 1444.6, 1445.6, 1446.7, 1447.7, 1448.7, 1449.8, 1450.8, 1451.8, 1452.9, 1453.9, 1455.0, 1456.0, 1457.0, 1458.1, 1459.1, 1460.1, 1461.2, 1462.2, 1463.2, 1464.3, 1465.3, 1466.3, 1467.4, 1468.4, 1469.4, 1470.5]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1983
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1984:
            old_indexing = indexing_base_year
            boundaries = [[2976.0, 2980.0], [2981.0, 2985.0], [2986.0, 2990.0], [2991.0, 2995.0], [2996.0, 3000.0], [3001.0, 3005.0], [3006.0, 3010.0], [3011.0, 3015.0], [3016.0, 3020.0], [3021.0, 3025.0], [3026.0, 3030.0], [3031.0, 3035.0], [3036.0, 3040.0], [3041.0, 3045.0], [3046.0, 3050.0], [3051.0, 3055.0], [3056.0, 3060.0], [3061.0, 3065.0], [3066.0, 3070.0], [3071.0, 3075.0], [3076.0, 3080.0], [3081.0, 3085.0], [3086.0, 3090.0], [3091.0, 3095.0], [3096.0, 3100.0], [3101.0, 3105.0], [3106.0, 3110.0], [3111.0, 3115.0], [3116.0, 3120.0], [3121.0, 3125.0], [3126.0, 3130.0], [3131.0, 3135.0], [3136.0, 3140.0], [3141.0, 3145.0], [3146.0, 10000000000000000]]
            benefits = [1523.0, 1524.0, 1525.0, 1526.1, 1527.1, 1528.1, 1529.2, 1530.2, 1531.2, 1532.3, 1533.3, 1534.3, 1535.4, 1536.4, 1537.4, 1538.5, 1539.5, 1540.5, 1541.6, 1542.6, 1543.7, 1544.7, 1545.7, 1546.8, 1547.8, 1548.8, 1549.9, 1550.9, 1551.9, 1553.0, 1554.0, 1555.0, 1556.1, 1557.1, 1558.1]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1984
                    break
                else:
                    indexing_base_year = old_indexing
        
        if retirement_year >= 1985:
            old_indexing = indexing_base_year
            boundaries = [[3156.0, 3160.0], [3161.0, 3165.0], [3166.0, 3170.0], [3171.0, 3175.0], [3176.0, 3180.0], [3181.0, 3185.0], [3186.0, 3190.0], [3191.0, 3195.0], [3196.0, 3200.0], [3201.0, 3205.0], [3206.0, 3210.0], [3211.0, 3215.0], [3216.0, 3220.0], [3221.0, 3225.0], [3226.0, 3230.0], [3231.0, 3235.0], [3236.0, 3240.0], [3241.0, 3245.0], [3246.0, 3250.0], [3251.0, 3255.0], [3256.0, 3260.0], [3261.0, 3265.0], [3266.0, 3270.0], [3271.0, 3275.0], [3276.0, 3280.0], [3281.0, 3285.0], [3286.0, 3290.0], [3291.0, 3295.0], [3296.0, 10000000000000000]]
            benefits = [1608.4, 1609.4, 1610.5, 1611.5, 1612.5, 1613.6, 1614.6, 1615.6, 1616.7, 1617.7, 1618.7, 1619.8, 1620.8, 1621.8, 1622.8, 1623.9, 1624.9, 1625.9, 1627.0, 1628.0, 1629.0, 1630.1, 1631.1, 1632.1, 1633.2, 1634.2, 1635.2, 1636.3, 1637.3]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1985
                    break
                else:
                    indexing_base_year = old_indexing
        
        if retirement_year >= 1986:
            old_indexing = indexing_base_year
            boundaries = [[3306.0, 3310.0], [3311.0, 3315.0], [3316.0, 3320.0], [3321.0, 3325.0], [3326.0, 3330.0], [3331.0, 3335.0], [3336.0, 3340.0], [3341.0, 3345.0], [3346.0, 3350.0], [3351.0, 3355.0], [3356.0, 3360.0], [3361.0, 3365.0], [3366.0, 3370.0], [3371.0, 3375.0], [3376.0, 3380.0], [3381.0, 3385.0], [3386.0, 3390.0], [3391.0, 3395.0], [3396.0, 3400.0], [3401.0, 3405.0], [3406.0, 3410.0], [3411.0, 3415.0], [3416.0, 3420.0], [3421.0, 3425.0], [3426.0, 3430.0], [3431.0, 3435.0], [3436.0, 3440.0], [3441.0, 3445.0], [3446.0, 3450.0], [3451.0, 3455.0], [3456.0, 3460.0], [3461.0, 3465.0], [3466.0, 3470.0], [3471.0, 3475.0], [3476.0, 3480.0], [3481.0, 3485.0], [3486.0, 3490.0], [3491.0, 3495.0], [3496.0, 10000000000000000]]
            benefits = [1660.6, 1661.6, 1662.6, 1663.6, 1664.6, 1665.6, 1666.6, 1667.7, 1668.7, 1669.7, 1670.7, 1671.7, 1672.7, 1673.7, 1674.7, 1675.8, 1676.8, 1677.8, 1678.8, 1679.8, 1680.8, 1681.8, 1682.8, 1683.9, 1684.9, 1685.9, 1686.9, 1687.9, 1688.9, 1689.9, 1691.0, 1692.0, 1693.0, 1694.0, 1695.0, 1696.0, 1697.0, 1698.0, 1699.1]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1986
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1987:
            old_indexing = indexing_base_year
            boundaries =[[3506.0, 3510.0], [3511.0, 3515.0], [3516.0, 3520.0], [3521.0, 3525.0], [3526.0, 3530.0], [3531.0, 3535.0], [3536.0, 3540.0], [3541.0, 3545.0], [3546.0, 3550.0], [3551.0, 3555.0], [3556.0, 3560.0], [3561.0, 3565.0], [3566.0, 3570.0], [3571.0, 3575.0], [3576.0, 3580.0], [3581.0, 3585.0], [3586.0, 3590.0], [3591.0, 3595.0], [3596.0, 3600.0], [3601.0, 3605.0], [3606.0, 3610.0], [3611.0, 3615.0], [3616.0, 3620.0], [3621.0, 3625.0], [3626.0, 3630.0], [3631.0, 3635.0], [3636.0, 3640.0], [3641.0, 3645.0], [3646.0, 1000000000000000]]
            benefits = [1772.5, 1773.5, 1774.6, 1775.6, 1776.7, 1777.7, 1778.7, 1779.8, 1780.8, 1781.9, 1782.9, 1784.0, 1785.0, 1786.0, 1787.1, 1788.1, 1789.2, 1790.2, 1791.3, 1792.3, 1793.3, 1794.4, 1795.4, 1796.5, 1797.5, 1798.5, 1799.6, 1800.6, 1801.7]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1987
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1988:
            old_indexing = indexing_base_year
            boundaries =[[3656.0, 3660.0], [3661.0, 3665.0], [3666.0, 3670.0], [3671.0, 3675.0], [3676.0, 3680.0], [3681.0, 3685.0], [3686.0, 3690.0], [3691.0, 3695.0], [3696.0, 3700.0], [3701.0, 3705.0], [3706.0, 3710.0], [3711.0, 3715.0], [3716.0, 3720.0], [3721.0, 3725.0], [3726.0, 3730.0], [3731.0, 3735.0], [3736.0, 3740.0], [3741.0, 3745.0], [3746.0, 1000000000000000000]]
            benefits = [1875.8, 1876.8, 1877.9, 1878.9, 1880.0, 1881.0, 1882.0, 1883.1, 1884.1, 1885.2, 1886.2, 1887.2, 1888.3, 1889.3, 1890.4, 1891.4, 1892.4, 1893.5, 1894.5]

            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1988
                    break
                else:
                    indexing_base_year = old_indexing

        if retirement_year >= 1989:
            old_indexing = indexing_base_year
            boundaries =[[3756.0, 3760.0], [3761.0, 3765.0], [3766.0, 3770.0], [3771.0, 3775.0], [3776.0, 3780.0], [3781.0, 3785.0], [3786.0, 3790.0], [3791.0, 3795.0], [3796.0, 3800.0], [3801.0, 3805.0], [3806.0, 3810.0], [3811.0, 3815.0], [3816.0, 3820.0], [3821.0, 3825.0], [3826.0, 3830.0], [3831.0, 3835.0], [3836.0, 3840.0], [3841.0, 3845.0], [3846.0, 3850.0], [3851.0, 3855.0], [3856.0, 3860.0], [3861.0, 3865.0], [3866.0, 3870.0], [3871.0, 3875.0], [3876.0, 3880.0], [3881.0, 3885.0], [3886.0, 3890.0], [3891.0, 3895.0], [3896.0, 3900.0], [3901.0, 3905.0], [3906.0, 3910.0], [3911.0, 3915.0], [3916.0, 3920.0], [3921.0, 3925.0], [3926.0, 3930.0], [3931.0, 3935.0], [3936.0, 3940.0], [3941.0, 3945.0], [3946.0, 3950.0], [3951.0, 3955.0], [3956.0, 3960.0], [3961.0, 3965.0], [3966.0, 3970.0], [3971.0, 3975.0], [3976.0, 3980.0], [3981.0, 3985.0], [3986.0, 3990.0], [3991.0, 3995.0], [3996.0, 10000000000000000.0]]
            benefits = [1985.6, 1986.6, 1987.7, 1988.7, 1989.8, 1990.8, 1991.9, 1992.9, 1994.0, 1995.0, 1996.1, 1997.1, 1998.1, 1999.2, 2000.2, 2001.3, 2002.3, 2003.4, 2004.4, 2005.5, 2006.5, 2007.6, 2008.6, 2009.7, 2010.7, 2011.8, 2012.8, 2013.9, 2014.9, 2015.9, 2017.0, 2018.0, 2019.1, 2020.1, 2021.2, 2022.2, 2023.3, 2024.3, 2025.4, 2026.4, 2027.5, 2028.5, 2029.6, 2030.6, 2031.7, 2032.7, 2033.7, 2034.8, 2035.8]
            for rowNum in range(len(boundaries)):
                if avg_monthly_wage>= boundaries[rowNum][0] and avg_monthly_wage <= boundaries[rowNum][1]:
                    monthly_benefits = benefits[rowNum]
                    indexing_base_year = 1989
                    break
                else:
                    indexing_base_year = old_indexing
        
    return (monthly_benefits, indexing_base_year)
        

def widow1973(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if (retirement_year >= widow_birth_year +60) and q1973(income_stream,index_year,birth_year, retirement_year,woman):
        spousal_benefit = 0
        if q1973(widow_income_stream, widow_index_year, widow_birth_year, widow_retirement_year, widow_woman):
            widowMonthlyBenefit = b1973(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_reference_year, widow_woman)
        else: widowMonthlyBenefit = 0
        primary_adjusted_income_stream=i1973(income_stream, index_year, retirement_year)
        primary_avg_monthly_wage = a1973(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman, death_year)
        primaryPIA = bb1973(income_stream, primary_avg_monthly_wage,index_year, birth_year,retirement_year, reference_year, woman)
        primaryMonthlyBenefit = b1973(income_stream, index_year, birth_year, retirement_year, reference_year, woman)
        
        #print("primpia: ", primaryPIA)
        #print("prim: ", primaryMonthlyBenefit)

        primaryPIA, indexing_base_year = tableMaxCalc(primaryPIA, primary_avg_monthly_wage, retirement_year)

        #print("primary: ", primaryPIA, indexing_base_year)
        #indexing_base_year = 1974
    
        
        for i in range(indexing_base_year+1,reference_year):
            #print(i, " applied: ", cola_adjustments[i+1], " and ", indexed_monthly_benefits*(1+cola_adjustments[i+1]))
            cola = (1+cola_adjustments[i+1]) 
            if i == 1999 and retirement_year > 2001: 
                cola = 1.025 #Pursuant to Public Law 106-554
            
            primaryPIA*=cola #this is actually not quite right, this smoothes how the adjustments are actually done seen on pages 7 and 8 of pdf, this actually probably produces a positive bias on long time scales of benefits paid outs
            #print(primaryPIA, i+1, (1+cola_adjustments[i+1]))
            primaryPIA = round(primaryPIA,4)
            if i < 1982:
                primaryPIA = math.ceil(primaryPIA * 10) / 10
            else:
                primaryPIA = math.floor(primaryPIA * 10) / 10

        #print("primary: ", primaryPIA)

        deduction = 1
        if (retirement_year <= widow_birth_year + 65):
            months = 12 * (widow_birth_year + 65 - retirement_year)

            deduction -= (19/40) * 0.01 * min(months, 60)

            if months > 60:
                extraMonths = 36 - months
                deduction -= (43/240) * 0.01 * extraMonths

        #print("ded: ", deduction)

        widow_benefit_guarantee_pre_cap = primaryPIA  * deduction
        widos_benefit_guarantee = widow_benefit_guarantee_pre_cap
        #spouse_benefit_guarantee = min(spouse_benefit_guarantee_pre_cap, max(primaryMonthlyBenefit, primaryPIA * .825))

        if reference_year < 1982:
            spouse_benefit_guarantee = math.ceil(widos_benefit_guarantee * 10) / 10
        else:
            spouse_benefit_guarantee = math.floor(widos_benefit_guarantee * 10) / 10

        widow_benefit = 0
        if widowMonthlyBenefit < widos_benefit_guarantee:
            widow_benefit = widos_benefit_guarantee - widowMonthlyBenefit


        if reference_year >= 1983:
            return math.floor(widow_benefit)
        elif reference_year >= 1977:
            return math.ceil(widow_benefit * 10) / 10
        else:
            return math.ceil(10*widow_benefit) /10

def MFB1973(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1973(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1973(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    
    avg_monthly_wage_list = [
    [0, 76], [77, 78], [79, 80], [81, 81], [82, 83], [84, 85], [86, 87], 
    [88, 89], [90, 90], [91, 92], [93, 94], [95, 96], [97, 97], [98, 99], 
    [100, 101], [102, 102], [103, 104], [105, 106], [107, 107], [108, 109], 
    [110, 113], [114, 118], [119, 122], [123, 127], [128, 132], [133, 136], 
    [137, 141], [142, 146], [147, 150], [151, 155], [156, 160], [161, 164], 
    [165, 169], [170, 174], [175, 178], [179, 183], [184, 188], [189, 193], 
    [194, 197], [198, 202], [203, 207], [208, 211], [212, 216], [217, 221], 
    [222, 225], [226, 230], [231, 235], [236, 239], [240, 244], [245, 249], 
    [250, 253], [254, 258], [259, 263], [264, 267], [268, 272], [273, 277], 
    [278, 281], [282, 286], [287, 291], [292, 295], [296, 300], [301, 305], 
    [306, 309], [310, 314], [315, 319], [320, 323], [324, 328], [329, 333], 
    [334, 337], [338, 342], [343, 347], [348, 351], [352, 356], [357, 361], 
    [362, 365], [366, 370], [371, 375], [376, 379], [380, 384], [385, 389], 
    [390, 393], [394, 398], [399, 403], [404, 407], [408, 412], [413, 417], 
    [418, 421], [422, 426], [427, 431], [432, 436], [437, 440], [441, 445], 
    [446, 450], [451, 454], [455, 459], [460, 464], [465, 468], [469, 473], 
    [474, 478], [479, 482], [483, 487], [488, 492], [493, 496], [497, 501], 
    [502, 506], [507, 510], [511, 515], [516, 520], [521, 524], [525, 529], 
    [530, 534], [535, 538], [539, 543], [544, 548], [549, 553], [554, 556], 
    [557, 560], [561, 563], [564, 567], [568, 570], [571, 574], [575, 577], 
    [578, 581], [582, 584], [585, 588], [589, 591], [592, 595], [596, 598], 
    [599, 602], [603, 605], [606, 609], [610, 612], [613, 616], [617, 620], 
    [621, 623], [624, 627], [628, 630], [631, 634], [635, 637], [638, 641], 
    [642, 644], [645, 648], [649, 652], [653, 656], [657, 660], [661, 665], 
    [666, 670], [671, 675], [676, 680], [681, 685], [686, 690], [691, 695], 
    [696, 700], [701, 705], [706, 710], [711, 715], [716, 720], [721, 725], 
    [726, 730], [731, 735], [736, 740], [741, 745], [746, 750], [751, 755], 
    [756, 760], [761, 765], [766, 770], [771, 775], [776, 780], [781, 785], 
    [786, 790], [791, 795], [796, 800], [801, 805], [806, 810], [811, 815], 
    [816, 820], [821, 825], [826, 830], [831, 835], [836, 840], [841, 845], 
    [846, 850], [851, 855], [856, 860], [861, 865], [866, 870], [871, 875], 
    [876, 880], [881, 885], [886, 890], [891, 895], [896, 900], [901, 905], 
    [906, 910], [911, 915], [916, 920], [921, 925], [926, 930], [931, 935], 
    [936, 940], [941, 945], [946, 950], [951, 955], [956, 960], [961, 965], 
    [966, 970], [971, 975], [976, 980], [981, 985], [986, 990], [991, 995], 
    [996, 1000], [1001, 1005], [1006, 1010], [1011, 1015], [1016, 1020], 
    [1021, 1025], [1026, 1030], [1031, 1035], [1036, 1040], [1041, 1045], 
    [1046, 1050], [1051, 1055], [1056, 1060], [1061, 1065], [1066, 1070], 
    [1071, 1075], [1076, 1080], [1081, 1085], [1086, 1090], [1091, 1095], 
    [1096, 10000000000000000000000000] #1100
    ]

    # Column V: Maximum Family Benefits
    maximum_family_benefits = [
        140.80, 143.00, 146.30, 149.00, 151.70, 154.80, 157.70, 160.20, 163.40, 
        166.20, 169.00, 171.60, 174.80, 177.80, 181.20, 183.80, 186.80, 190.20, 
        193.20, 196.40, 199.40, 202.20, 205.40, 208.40, 211.70, 214.50, 217.40, 
        220.70, 223.70, 226.50, 229.80, 232.70, 235.80, 238.90, 241.80, 245.10, 
        247.80, 251.40, 254.40, 257.10, 260.60, 263.60, 266.10, 269.40, 272.40, 
        275.70, 278.70, 282.20, 286.20, 292.10, 296.80, 302.60, 308.40, 313.10, 
        319.00, 324.80, 329.50, 335.40, 341.30, 345.90, 351.70, 357.60, 362.40, 
        368.20, 374.10, 378.80, 384.70, 390.50, 395.20, 401.00, 406.90, 411.50, 
        417.40, 423.30, 428.00, 433.80, 439.60, 444.50, 450.30, 456.10, 460.80, 
        466.70, 472.60, 477.20, 483.10, 488.90, 493.60, 499.40, 505.30, 511.20, 
        513.50, 516.50, 519.40, 521.70, 524.60, 527.50, 530.00, 532.80, 535.80, 
        538.20, 541.20, 544.10, 546.40, 549.30, 552.20, 554.60, 557.50, 560.50, 
        562.70, 565.70, 568.60, 571.00, 573.90, 576.80, 579.80, 581.50, 583.90, 
        585.70, 588.00, 589.80, 592.00, 593.90, 596.10, 597.00, 600.30, 602.00, 
        604.40, 606.10, 608.60, 610.30, 612.50, 614.40, 616.70, 619.10, 620.80, 
        623.20, 625.30, 628.40, 631.30, 634.40, 637.20, 640.30, 643.10, 645.00, 
        646.70, 649.10, 651.40, 653.70, 656.10, 658.40, 660.70, 663.10, 665.40, 
        667.70, 670.00, 672.40, 674.70, 677.00, 679.40, 681.70, 684.00, 686.40, 
        688.70, 690.70, 692.60, 694.60, 696.50, 698.50, 700.30, 702.30, 704.20, 
        706.20, 708.10, 710.10, 712.00, 714.00, 715.00, 717.00, 719.80, 721.80, 
        723.70, 725.70, 727.50, 729.50, 731.40, 733.40, 735.30, 737.30, 739.20, 
        741.20, 743.10, 745.10, 747.00, 749.00, 750.90, 752.90, 754.70, 756.70, 
        758.60, 760.60, 762.50, 764.50, 766.40, 768.40, 770.30, 772.30, 774.20, 
        776.20, 778.00, 780.00, 781.90, 783.00, 785.80, 787.50, 789.30, 791.00, 
        792.80, 794.50, 796.30, 798.00, 799.80, 801.50, 803.30, 805.00, 806.80, 
        808.50, 810.30, 812.00, 813.80, 815.50, 817.30, 819.00, 820.80
    ]
    for i in range(len(avg_monthly_wage_list)):
            if math.ceil(primary_avg_monthly_wage)>=avg_monthly_wage_list[i][0] and primary_avg_monthly_wage<=avg_monthly_wage_list[i][1]: 
                maximum_family_benefit=maximum_family_benefits[i]

    for i in range(1974,reference_year):
        #print(i, " applied: ", cola_adjustments[i+1], " and ", indexed_monthly_benefits*(1+cola_adjustments[i+1]))
        cola = (1+cola_adjustments[i+1]) 
        if i == 1999 and retirement_year > 2001: 
            cola = 1.025 #Pursuant to Public Law 106-554
        
        maximum_family_benefit*=cola

    if maximum_family_benefit: return math.floor(maximum_family_benefit*10) /10
    else: return 0

def children1973(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
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
    primary_adjusted_income_stream=i1973(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1973(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman, death_year)
    primary_PIA = bb1973(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)

    primary_PIA, indexingYear = tableMaxCalc(primary_PIA, primary_avg_monthly_wage, retirement_year)

    for i in range(indexingYear + 1,reference_year):
        #print(i, " applied: ", cola_adjustments[i+1], " and ", indexed_monthly_benefits*(1+cola_adjustments[i+1]))
        cola = (1+cola_adjustments[i+1]) 
        if i == 1999 and retirement_year > 2001: 
            cola = 1.025 #Pursuant to Public Law 106-554
        
        primary_PIA*=cola #this is actually not quite right, this smoothes how the adjustments are actually done seen on pages 7 and 8 of pdf, this actually probably produces a positive bias on long time scales of benefits paid outs
        primary_PIA = round(primary_PIA,4)
        if i < 1982:
            primary_PIA = math.ceil(primary_PIA * 10) / 10
        else:
            primary_PIA = math.floor(primary_PIA * 10) / 10

    if reference_year >= death_year: #If the primary is dead
        return math.ceil(0.75*primary_PIA*10)/10
    else: 
        return math.ceil(0.5* primary_PIA*10)/10