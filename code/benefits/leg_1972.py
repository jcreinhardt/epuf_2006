#!/usr/bin/env python
# coding: utf-8

# In[30]:


#By Daniel Carrillo
#1972 coded legislation
#These data inputs might have to be adjusted and tested later


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
    2000: 0.025,
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



#pdf page 12-13 in 1972 minor
def i1972(income_stream:list, index_year:int, retirement_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1967 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy() #i could redo all of these as dictionaries?
    for i in range(len(income_stream)):
        if income_stream[i]>0 and (index_year+i)<1951:
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
        last_base_year=1977
        
        if (index_year+i)>1977: #this is the indexing of the contribution base found on page 13 of 1972, I think this code is inefficient, it's looping too many times, we could move the generating part outside         
            taxable_maximum=16500
            for k in range(1978, index_year+i): 
                if cpi[k]>1.03*cpi[last_base_year]:
                    cpi_increase=cpi[k]/cpi[last_base_year]
                    taxable_maximum=taxable_maximum*cpi_increase
                    last_base_year=k
            if income_stream[i]>taxable_maximum: #this is actually still missing a rounding adjustment from page 13 of pdf
                adjusted_income_stream[i]=taxable_maximum
    return adjusted_income_stream



# @Daniel I don't think this changed since 1960 please double check me! I don't think it has either!

def a1972(adjusted_income_stream:list, original_income_stream, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, death_year = 0):
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

    #elasped_years = 19

    #print(elasped_years)

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
    
    #print("avg monthly wage: ", avg_monthly_wage)
    return math.floor(avg_monthly_wage)
    
#see 1961 pdf page 7, has not been updated since thens
def q1972(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, woman:bool, skip1939 = False): #this might not be completely correct/ might be off by half a year
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
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    for i in range(len(adjusted_income_stream)):
        if adjusted_income_stream[i]>= 50 and adjusted_income_stream[i] < 100:
            coverage_quarters+=1
        elif adjusted_income_stream[i] >= 100 and adjusted_income_stream[i] < 150:
            coverage_quarters+= 2
        elif adjusted_income_stream[i] >= 150 and adjusted_income_stream[i] < 200:
            coverage_quarters+= 3
        elif adjusted_income_stream[i] >= 200:
            coverage_quarters+= 4
    #print(coverage_quarters)
    reference_year=max(1951,birth_year+21) #odd nuance of the legislation
    end_year = birth_year +62
    '''
    if woman==True:
        end_year=max(1961,birth_year+62)
    elif birth_year<1911:
        end_year= max(1961,birth_year+65) #these can be found on page 13 of 1972 pdf
    elif birth_year==1911:
        end_year=max(1961,birth_year+64)
    elif birth_year==1912:
        end_year=max(1961,birth_year+63)
    else:
        end_year= max(1961,birth_year+62)
    '''
    #reference_year=max(1951,birth_year+21) #odd nuance of the legislation
    if coverage_quarters>40:
        return True
    elif ((coverage_quarters)>=((4/4)*(end_year)-reference_year)) and (coverage_quarters>=6): #Temporarily Cut
        return True
    else:
        return False
        
def qcurrent1972(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
    """This function determines whether an individual is considered fully-insured as of the 1939 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int)
        income_stream -- a list of nominal incomes a person received in each year
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """

    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    if len(income_stream) < 3 or death_year >= reference_year : return False
    for i in income_stream[-3:]:
        if income_stream[i]>=200:
            coverage_quarters+=4
        elif income_stream[i] >=150:
            coverage_quarters +=3
        elif income_stream[i] >=100:
            coverage_quarters +=2
        elif income_stream[i] >=100:
            coverage_quarters +=1
    
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


'''#do we need this?
def getYearsOfCover(inc_str:list, index_year:int):
    """ This function takes in 
        - inc_str which is the list of incs history
        - index_year which is the year associated with the first indexed inc in inc_str
        
        This function calculates the years of covereage according to pdf page 5 (or page 1333) in 1972 major pdf."""
    # Get the years_of_coverage pdf page 5 and page 1333 in 1972 major
    if index_year < 1951:
        sum_wage_before_1951 = sum(inc for idx, inc in enumerate(inc_str) if idx + index_year < 1951)
    else:
        sum_wage_before_1951 = 0

    years_of_coverage = sum_wage_before_1951/900 + sum(1 for idx in range(0,len(inc_str)) if idx + index_year > 1950)
    years_of_coverage = min(years_of_coverage, 30) 
    
    return years_of_coverage'''

#This changed in 72 minor
def bb1972(income_stream:list, original_income_stream:list, avg_monthly_wage:int, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
#def bb1972(inc_str:list, index_year:int, birth_year:int, retirement_year, woman:bool):

    #retirement_year = index_year + len(inc_str) #these need to be fixed across the board!!!
    adjusted_income_stream=income_stream
    #avg_monthly_wage=a1972(adjusted_income_stream, index_year, birth_year, woman)
    pia_1971 = 0
    pib = 0
    # Remove zeros in-place
    inc_str = [value for value in adjusted_income_stream if value != 0]
    

    years_of_coverage = getYearsOfCover(inc_str, index_year)

    if (birth_year+65<1950): #this checks if they are old enough to have a pib; someone who did have a pib would receive a new updated pia based on these charts below, if they do they go through the formulas differently. This is what the tables primarily deal with.
        pib=b1939(i1939(original_income_stream, index_year, retirement_year),index_year, index_year, birth_year, retirement_year, reference_year, woman)
    elif (birth_year+65<1973):
        pia_1971=b1971(i1971(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year,retirement_year, reference_year, woman)
  
        
    col1 = [
        [0, 16.21], [16.21, 16.85], [16.85, 17.61], [17.61, 18.41], [18.41, 19.25],
        [19.25, 20.01], [20.01, 20.65], [20.65, 21.29], [21.29, 21.89], [21.89, 22.29],
        [22.29, 22.69], [22.69, 23.09], [23.09, 23.45], [23.45, 23.77], [23.77, 24.21],
        [24.21, 24.61], [24.61, 25.01], [25.01, 25.49], [25.49, 25.93], [25.93, 26.41],
        [26.41, 26.95], [27.47, 28.01], [28.01, 28.69], [28.69, 29.26], [29.26, 29.69],
        [29.69, 30.37], [30.37, 30.93], [30.93, 31.37], [31.37, 32.01], [32.01, 32.61],
        [32.61, 33.21], [33.21, 33.89], [33.89, 34.51], [34.51, 35.01], [35.01, 35.81],
        [35.81, 36.81], [36.41, 37.09], [37.09, 37.61], [37.61, 38.21], [38.21, 39.13],
        [39.13, 39.69], [39.69, 40.34], [40.34, 41.13], [41.13, 41.77], [41.77, 42.45],
        [42.45, 43.21], [43.21, 43.77], [43.77, 44.45], [44.45, 44.89], [44.89, 45.61]
    ]

     
    col2 = [70.4, 71.5, 73.1, 74.5, 75.8,
    77.4, 78.8, 80.1, 81.7, 83.1,
    84.5, 85.8, 87.4, 88.9, 90.6,
    91.9, 93.4, 95.1, 96.6, 98.2,
    99.7, 101.1, 102.7, 104.2, 105.9,
    107.3, 108.7, 110.4, 111.9, 113.3,
    115.0, 116.4, 118.0, 119.5, 121.0,
    122.6, 124.0, 125.7, 127.2, 128.6,
    130.3, 131.8, 133.1, 134.8, 136.3,
    137.9, 139.4, 141.1, 142.5, 143.9,
    145.6, 147.1, 148.4, 150.1, 151.6,
    153.2, 154.7, 156.2, 157.9, 159.2,
    160.9, 162.4, 163.8, 165.5, 166.9,
    168.3, 170.0, 171.5, 173.2, 174.5,
    176.0, 177.7, 179.1, 180.8, 182.2,
    183.6, 185.3, 186.8, 188.5, 189.8,
    191.3, 193.0, 194.4, 196.1, 197.4,
    198.8, 200.2, 201.8, 203.1, 204.5,
    206.1, 207.4, 208.8, 210.4, 211.7,
    213.1, 214.5, 216.1, 217.4, 218.8,
    220.4, 221.7, 223.1, 224.7, 226.0,
    227.4, 228.8, 230.3, 231.7, 233.1,
    234.7, 236.0, 237.4, 239.0, 240.3,
    241.7, 242.9, 244.2, 245.5, 246.8,
    248.0, 249.3, 250.5, 251.8, 253.0,
    254.4, 255.6, 256.9, 258.1, 259.4, 260.6,
    262.0, 263.2, 264.5, 265.7, 267.0,
    268.2, 269.5, 270.8, 272.1, 273.3,
    274.6, 275.8, 276.6, 277.4, 278.4,
    279.4, 280.4, 281.4, 282.4, 283.4,
    284.4, 285.4, 286.4, 287.4, 288.4,
    289.4, 290.4, 291.4, 292.4, 293.4,
    294.4, 295.4]

    col3 = [
        [0, 77], [77.0, 79.0], [79.0, 81.0], [81.0, 82.0], [82.0, 84.0],
        [84.0, 86.0], [86.0, 88.0], [88.0, 90.0], [90.0, 91.0], [91.0, 93.0],
        [93.0, 95.0], [95.0, 97.0], [97.0, 98.0], [98.0, 100.0], [100.0, 102.0],
        [102.0, 103.0], [103.0, 105.0], [105.0, 107.0], [107.0, 108.0], [108.0, 110.0],
        [110.0, 114.0], [114.0, 119.0], [119.0, 123.0], [123.0, 128.0], [128, 133],
        [133, 137], [137, 142], [142, 147], [147, 151], [151, 156],
        [156, 161], [161, 165], [165, 170], [170, 175], [175, 179],
        [179, 184], [184, 189], [189, 194], [194, 198], [198, 203],
        [203, 208], [208, 212], [212, 217], [217, 222], [222, 226],
        [226, 231], [231, 236], [236, 240], [240, 245], [245, 250],
        [250, 254], [254, 259], [259, 264], [264, 268], [268, 273],
        [273, 278], [278, 282], [282, 287], [287, 292], [292, 296],
        [296, 301], [301, 306], [306, 310], [310, 315], [315, 320],
        [320, 324], [324, 329], [329, 334], [334, 338], [338, 343],
        [343, 348], [348, 352], [352, 357], [357, 362], [362, 366],
        [366, 371], [371, 376], [376, 380], [380, 385], [385, 390],
        [390, 394], [394, 399], [399, 404], [404, 408], [408, 413],
        [413, 418], [418, 422], [422, 427], [427, 432], [432, 437],
        [437, 441], [441, 446], [446, 451], [451, 455], [455, 460],
        [460, 465], [465, 469], [469, 474], [474, 479], [479, 483],
        [483, 488], [488, 493], [493, 497], [497, 502], [502, 507],
        [507, 511], [511, 516], [516, 521], [521, 525], [525, 530],
        [530, 535], [535, 539], [539, 544], [544, 549], [549, 554],
        [554, 557], [557, 561], [561, 564], [564, 568], [568, 571],
        [571, 575], [575, 578], [578, 582], [582, 585], [585, 589],
        [589, 592], [592, 596], [596, 599], [599, 603], [603, 606],
        [606, 610], [610, 613], [613, 617], [617, 621], [621, 624],
        [624, 628], [628, 631], [631, 635], [635, 638], [638, 642],
        [642, 645], [645, 649], [649, 653], [653, 657], [657, 661],
        [661, 666], [666, 671], [671, 676], [676, 681], [681, 686],
        [686, 691], [691, 696], [699, 701], [701, 706], [706, 711],
        [711, 716], [716, 721], [721, 726], [726, 731], [731, 736],
        [736, 741], [741, 746], [746, 751], [751, 756], [756, 761],
        [761, 766], [766, 771], [771, 776], [776, 781], [781, 786],
        [786, 791], [791, 796], [796, 801], [801, 806], [806, 811],
        [811, 816], [816, 821], [821, 826], [826, 831], [831, 836],
        [836, 841], [841, 846], [846, 851], [851, 856], [856, 861],
        [861, 866], [866, 871], [871, 876], [876, 881], [881, 886],
        [886, 891], [891, 896], [896, 901], [901, 906], [906, 911],
        [911, 916], [916, 921], [921, 926], [926, 931], [931, 936],
        [936, 941], [941, 946], [946, 951], [951, 956], [956, 961],
        [961, 966], [966, 971], [971, 976], [976, 981], [981, 986],
        [986, 991], [991, 996], [996, 1001]
    ]


    col4 = [84.5, 85.8, 87.8, 89.4, 91.0,
    92.9, 94.6, 96.2, 98.1, 99.8,
    101.4, 103.0, 104.9, 106.7, 108.8,
    110.3, 112.1, 114.2, 116.0, 117.9,
    119.7, 121.4, 123.3, 125.1, 127.1,
    128.8, 130.5, 132.5, 134.3, 136.0,
    138.0, 139.7, 141.6, 143.4, 145.2,
    147.2, 148.8, 150.9, 152.7, 154.4,
    156.4, 158.2, 159.8, 161.8, 163.6,
    165.5, 167.3, 169.4, 171.0, 172.7,
    174.8, 176.6, 178.1, 180.2, 182.0,
    183.9, 185.7, 187.5, 189.5, 191.1,
    193.1, 194.9, 196.6, 198.6, 200.3,
    202.0, 204.0, 205.8, 207.9, 209.4,
    211.2, 213.3, 215.0, 217.0, 218.7,
    220.4, 222.4, 224.2, 226.2, 227.8,
    229.6, 231.6, 233.3, 235.4, 236.9,
    238.6, 240.3, 242.2, 243.8, 245.4,
    247.4, 248.9, 250.6, 252.6, 254.1,
    255.8, 257.4, 259.4, 260.9, 262.6,
    264.5, 266.1, 267.8, 269.7, 271.2,
    272.9, 274.6, 276.4, 278.1, 279.8,
    281.7, 283.2, 284.9, 286.8, 288.4,
    290.1, 291.5, 293.1, 294.6, 296.2,
    297.6, 299.2, 300.6, 302.2, 303.6,
    305.3, 306.8, 308.3, 309.8, 311.3,
    312.8, 314.4, 315.9, 317.4, 318.9,
    320.4, 321.9, 323.4, 325.0, 326.6,
    328.0, 329.6, 331.0, 332.0, 332.9,
    334.1, 335.3, 336.5, 337.7, 338.9,
    340.1, 341.3, 342.5, 343.7, 344.9,
    346.1, 347.3, 348.5, 349.7, 350.9,
    352.1, 353.3, 354.5, 355.5, 356.5,
    357.5, 358.5, 359.5, 360.5, 361.5,
    362.5, 363.5, 364.5, 365.5, 366.5,
    367.5, 368.5, 369.5, 370.5, 371.5,
    372.5, 373.5, 374.5, 375.5, 376.5,
    377.5, 378.5, 379.5, 380.5, 381.5,
    382.5, 383.5, 384.5, 385.5, 386.5,
    387.5, 388.5, 389.5, 390.5, 391.5,
    392.5, 393.5, 394.5, 395.5, 396.5,
    397.5, 398.5,399.5, 400.5, 401.5, 
    402.5, 403.5, 404.5]
    

    pia_under_1939 = 0
    pia_under_1971 = 0
    pia_under_avg_wage = 0


    #######################
    #this is the yearly inflation adjustments, found in pdf page 7-9 of 1972 pdf, this probably requires testing
    # last_base_year=1974
    # for i in range(1975, retirement_year): 
    #     if cpi[1974]>1.03*cpi[last_base_year]: 
    #         new_col2=[]
    #         for i in range(len(col2)):
    #             new_col2.append(col4[i])
    #         col2=new_col2
    #         cpi_increase=cpi[i-1974]/cpi[i-last_base_year]
    #         col4=[x*cpi_increase for x in col4] 

    #     if i==1974: #this code is horribly inefficient by my (DAC) own's admitting. A proper refactor would turn the contribution base into dictionaries. However, I'm unsure of the added value since i doubt this particularly script will ultimately be used much.
    #         contribution_base=13200
    #     if i==1975:
    #         contribution_base=14100
    #     if i==1976:
    #         contribution_base=15300
    #     if i==1977:
    #         contribution_base=16500         
    #     last_base_year_2=1977  
    #     cpi_increase=1
    #     if (i)>1977: #this is the indexing of the contribution base found on page 13 of 1972, I think this code is inefficient, it's looping too many times, we could move the generating part outside         
    #         contribution_base=16500
    #         for k in range(1978, retirement_year+1): 
    #             if cpi[k]>1.03*cpi[last_base_year]:
    #                 cpi_increase=cpi[k]/cpi[last_base_year]
    #                 contribution_base=contribution_base*cpi_increase
    #                 last_base_year_2=k
    #     while not col3[-1][1]<(1/12)*contribution_base:
    #         col3.append([col3[-1][0]+5,col3[-1][1]+5])
    #     while not col4[-1]<(.2)*(1/12)*(contribution_base-(contribution_base/cpi_increase)):
    #         col4.append(col4[-1]+1)        

    #     last_base_year=i


    # rowNum is the row od the table
    if ((q1972(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year,woman)==True) and (birth_year+65<1950)):
        for rowNum in range(len(col1)):
            if pib>= col1[rowNum][0] and pib <= col1[rowNum][1]:
                pia_under_1939 = col4[rowNum]
        
    #get pia based on col 2 # @Daniel this hsould be based on 71 benefits we are missing a year
    if ((q1972(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year,woman)==True) and (birth_year+65<1972)):
        if pia_1971 <= col2[0]:
            pia_under_1971 = col4[0]
        else:    
            for rowNum in range(1,len(col2)): # we checked the first case. Now we check all other values
                if round(pia_1971, 2) == col2[rowNum]: # Rounded to 2 decimals
                    pia_under_1971 = col4[rowNum]

    # get pia based on co 3 avg mon wage
    #get pia based on col3
    for rowNum in range(len(col3)):
        if avg_monthly_wage >= col3[rowNum][0] and avg_monthly_wage <= col3[rowNum][1]:
            pia_under_avg_wage = col4[rowNum]
    
    
    #1972 max, Sec 101 (a) (3), 1333, page 5 of pdf
    years_of_coverage=getYearsOfCover(inc_str, index_year)
    pia_1972= 8.50*max((years_of_coverage-10),0)

    pia = max(pia_under_1939, pia_under_1971, pia_under_avg_wage, pia_1972)
    return pia


# In[25]:


def b1972(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """ 
    monthly_benefits=0
    #retirement_year=index_year+len(income_stream)
    adjusted_income_stream=i1972(income_stream, index_year, retirement_year)

    if retirement_year <= 1950: average_monthly_wage = a1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1952 : average_monthly_wage = a1950(i1950(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1954: average_monthly_wage = a1952(i1952(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1956: average_monthly_wage=a1954(i1954(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1958: average_monthly_wage = a1956(i1956(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1960: average_monthly_wage=a1958(i1958(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1961: average_monthly_wage=a1960(i1960(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1965: average_monthly_wage=a1961(i1961(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1967: average_monthly_wage = a1965(i1965(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1969:  average_monthly_wage = a1967(i1967(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, reference_year, reference_year, woman)
    elif retirement_year <= 1971: average_monthly_wage = a1969(i1969(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1972: average_monthly_wage=a1971(i1971(original_income_stream, index_year, retirement_year), original_income_stream, index_year, birth_year,retirement_year, reference_year, woman)
    else: average_monthly_wage = a1972(adjusted_income_stream, original_income_stream,  index_year, birth_year, retirement_year, reference_year, woman)

    monthly_benefits=bb1972(adjusted_income_stream, original_income_stream, average_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)#bb1972(income_stream, index_year, birth_year, retirement_year, woman)
    #print("monthly: ", monthly_benefits)
#ChatGpt wrote the following block because my code messed up -- DCarrillo
###########
    nra = 65
    age_at_retirement = retirement_year - birth_year
    #print("retirement: ", retirement_year)
    
    if age_at_retirement < nra:
        # Early retirement deduction: 0.556% per month early
        early_deduction = 12 * 0.00556 * (nra - age_at_retirement)
        monthly_benefits = (1 - early_deduction) * monthly_benefits
        #print(early_deduction)

    elif age_at_retirement > nra:
        # Delayed retirement credit, starting from 1971 and capped at age 72
        retirement_age = retirement_year - birth_year
        max_credit_year = min(birth_year + 72, retirement_year)
        credit_years = max(max_credit_year - (birth_year + nra), 0)
        effective_start_year = max(birth_year + nra, 1971)
        actual_credit_years = max(max_credit_year - effective_start_year, 0)
    
        late_credit = 0.01 * actual_credit_years
        #print("late: ", late_credit)
        monthly_benefits = (1 + late_credit) * monthly_benefits
    
    #print("the monthly benefits are: ", monthly_benefits)
#############
    indexed_monthly_benefits=monthly_benefits #explain how the inflation function works
    
    for i in range(1975,reference_year):
        indexed_monthly_benefits*=(1+cola_adjustments[i+1]) #this is actually not quite right, this smoothes how the adjustments are actually done seen on pages 7 and 8 of pdf, this actually probably produces a positive bias on long time scales of benefits paid outs
  
    
#this is actually not quite right, this smoothes how the adjustments are actually done seen on pages 7 and 8 of pdf, this actually probably produces a positive bias on long time scales of benefits paid outs
    
    return math.ceil(indexed_monthly_benefits*10)/10


# pdf page 16 of 1972 minor pdf. Note that they report full OASDI taxes, not just OASI, so DI must be subtracted from them.
#note that disability insurance taxes is now active, these can be found on page 255 of 1969 pdf (NEEDS TO BE UPDATED WITH PAGE 36 of 1972 pdf)
def t1972(income_stream:list, index_year:int):
    
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    capped_income_stream=i1972(income_stream, index_year, index_year + len(income_stream)) #to apply the taxable maximums to the benefit stream
    
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
        if (index_year+i) >=1971 and income_stream[i] <=1977: 
             employee_tax_rate= 0.0405
             employer_tax_rate= 0.0405
             disability_tax=.0110
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1978 and income_stream[i] <=2010: 
             employee_tax_rate= 0.0395
             employer_tax_rate= 0.0395
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=2011: 
             employee_tax_rate= 0.048
             employer_tax_rate= 0.048
             disability_tax=.0110
             nominal_contributions.append(capped_income_stream[i]*employee_tax_rate)
    return nominal_contributions



def death1972(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    woman: This is TRUE if the deceased was female.
    '''
    if (q1972(income_stream, index_year, birth_year, woman)): 
        monthlyBenefits = b1972(income_stream, index_year, birth_year, retirement_year, woman)
        return max(3 * monthlyBenefits, 255)
    else:
        return 0
    

def spouse1972(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    if q1972(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_woman):
        spouse_benefit = b1972(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    primary_adjusted_income_stream=i1972(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1972(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1972(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)
    
    #print("primary: ", primary_PIA)
    deduction = 1

    if spouse_birth_year + 65 > spouse_retirement_year:
        deduction = deduction - (25/36) * 0.01 * 12 *(spouse_birth_year+65 - spouse_retirement_year)

    spouse_benefit_guarantee = 0.5*primary_PIA *deduction
    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    return math.ceil(spousal_benefit*10)/10 #in 1972, spousal benefits began to increase with COLA. However, if b1972 and bb1972 account for these COLA adjustments, we do not need to account again here.


def widow1972(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if (retirement_year >= widow_birth_year +60) and q1972(income_stream,index_year,birth_year,retirement_year, woman):
        spousal_benefit = 0
        if q1972(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_woman):
            widowMonthlyBenefit = b1972(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_reference_year,widow_woman)
        else: widowMonthlyBenefit = 0
        adjusted_income_stream=i1972(income_stream, index_year, retirement_year)
        avg_monthly_wage = a1972(adjusted_income_stream, index_year, birth_year, retirement_year, reference_year, woman, death_year)
        primaryPIA = bb1972(income_stream, avg_monthly_wage, index_year, birth_year,retirement_year,reference_year, woman)
        primaryMonthlyBenefit = b1972(income_stream, index_year, birth_year, retirement_year, reference_year, woman)
        #print("avg: " ,avg_monthly_wage)
        #print("PIA: ", primaryPIA)
        deduction = 1
        if (retirement_year <= widow_birth_year + 65):
            months = 12 * (widow_birth_year + 65 - retirement_year)

            deduction -= (19/40) * 0.01 * min(months, 60)

            if months > 60:
                extraMonths = 36 - months
                deduction -= (43/240) * 0.01 * extraMonths

        #print("ded: ", deduction)

        widow_benefit_guarantee_pre_cap = primaryPIA  * deduction
        widow_benefit_guarantee = widow_benefit_guarantee_pre_cap

        #print("here: ", spouse_benefit_guarantee_pre_cap)
        #print("spousal: ", widowMonthlyBenefit)
        #spouse_benefit_guarantee = min(spouse_benefit_guarantee_pre_cap, max(primaryMonthlyBenefit, primaryPIA * .825))

        widowBenefit = 0
        if widowMonthlyBenefit < widow_benefit_guarantee:
            widowBenefit = widow_benefit_guarantee - widowMonthlyBenefit

        return math.ceil(widowBenefit*10)/10
    else:
        return 0
    

def MFB1972(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1972(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1972(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
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
    [996, 1000]
    ]

    # Column V: Maximum Family Benefits
    maximum_family_benefits = [
        126.80, 128.80, 131.70, 134.20, 136.50, 139.40, 141.90, 144.30, 147.20, 
        149.70, 152.20, 154.50, 157.40, 160.10, 163.20, 165.50, 168.20, 171.30, 
        173.90, 176.90, 179.60, 182.10, 185.00, 187.70, 190.70, 193.20, 195.80, 
        198.80, 201.50, 204.00, 207.00, 209.60, 212.40, 215.20, 217.80, 220.80, 
        223.20, 226.40, 229.10, 231.60, 234.60, 237.30, 239.70, 242.70, 245.40, 
        248.30, 251.00, 254.10, 257.80, 260.10, 267.30, 272.60, 277.80, 282.00, 
        287.30, 292.60, 296.80, 302.10, 307.40, 311.60, 316.80, 322.10, 326.40, 
        331.70, 337.00, 341.20, 346.50, 351.80, 356.00, 361.20, 366.50, 370.70, 
        376.00, 381.30, 385.50, 390.80, 396.00, 400.40, 405.60, 410.90, 415.10, 
        420.40, 425.70, 429.90, 435.20, 440.40, 444.60, 449.90, 455.20, 460.50, 
        462.60, 465.30, 467.90, 470.00, 472.60, 475.20, 477.40, 480.00, 482.70, 
        484.80, 487.50, 490.10, 492.20, 494.80, 497.40, 499.60, 502.20, 504.90, 
        506.90, 509.60, 512.20, 514.40, 517.00, 519.60, 522.30, 523.80, 526.00, 
        527.60, 529.70, 531.30, 533.30, 535.00, 537.00, 538.60, 540.80, 542.30, 
        544.50, 546.00, 548.20, 549.80, 551.80, 553.50, 555.50, 557.70, 559.20, 
        561.40, 563.30, 566.10, 568.70, 571.50, 574.00, 576.80, 579.30, 581.00, 
        582.60, 584.70, 586.80, 588.90, 591.00, 593.10, 595.20, 597.30, 599.40, 
        601.50, 603.60, 605.70, 607.80, 609.90, 612.00, 614.10, 616.20, 618.30, 
        620.40, 622.20, 623.90, 625.70, 627.40, 629.20, 630.90, 632.70, 634.40, 
        636.20, 637.90, 639.70, 641.40, 643.20, 644.90, 646.70, 648.40, 650.20, 
        651.90, 653.70, 655.40, 657.20, 658.90, 660.70, 662.40, 664.20, 665.90, 
        667.70, 669.40, 671.20, 672.90, 674.70, 676.40, 678.20, 679.90, 681.70, 
        683.40, 685.20, 686.90, 688.70, 690.40, 692.20, 693.90, 695.70, 697.40, 
        699.20, 700.90, 702.70, 704.40, 706.20, 707.90]

    for i in range(len(avg_monthly_wage_list)):
            if primary_avg_monthly_wage>=avg_monthly_wage_list[i][0] and primary_avg_monthly_wage<=avg_monthly_wage_list[i][1]: 
                maximum_family_benefit=maximum_family_benefits[i]


    if maximum_family_benefit: return maximum_family_benefit
    else: return 0


def children1972(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
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
    primary_adjusted_income_stream=i1972(income_stream, index_year, retirement_year)
    if reference_year < death_year:
        primary_avg_monthly_wage = a1972(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    else:
        primary_avg_monthly_wage = a1972(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman, death_year)
    primary_PIA = bb1972(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)

    if reference_year >= death_year: #If the primary is dead
        return math.ceil(0.75*primary_PIA*10)/10
    else: 
        return math.ceil(0.5* primary_PIA*10)/10