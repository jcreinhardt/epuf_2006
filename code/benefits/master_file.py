from leg_1939 import *
from leg_1942 import *
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
from leg_1973 import *
from leg_1977 import *
from leg_modern import *


cpi_data = {
    1913: 9.9, 1914: 10, 1915: 10.1, 1916: 10.9, 1917: 12.8,
    1918: 15, 1919: 17.3, 1920: 20, 1921: 17.9, 1922: 16.8,
    1923: 17.1, 1924: 17.1, 1925: 17.5, 1926: 17.7, 1927: 17.4,
    1928: 17.2, 1929: 17.2, 1930: 16.7, 1931: 15.2, 1932: 13.6,
    1933: 12.9, 1934: 13.4, 1935: 13.7, 1936: 13.9, 1937: 14.4,
    1938: 14.1, 1939: 13.9, 1940: 14, 1941: 14.7, 1942: 16.3,
    1943: 17.3, 1944: 17.6, 1945: 18, 1946: 19.5, 1947: 22.3,
    1948: 24, 1949: 23.8, 1950: 24.1, 1951: 26, 1952: 26.6,
    1953: 26.8, 1954: 26.9, 1955: 26.8, 1956: 27.2, 1957: 28.1,
    1958: 28.9, 1959: 29.2, 1960: 29.6, 1961: 29.9, 1962: 30.3,
    1963: 30.6, 1964: 31, 1965: 31.5, 1966: 32.5, 1967: 33.4,
    1968: 34.8, 1969: 36.7, 1970: 38.8, 1971: 40.5, 1972: 41.8,
    1973: 44.4, 1974: 49.3, 1975: 53.8, 1976: 56.9, 1977: 60.6,
    1978: 65.2, 1979: 72.6, 1980: 82.4, 1981: 90.9, 1982: 96.5,
    1983: 99.6, 1984: 103.9, 1985: 107.6, 1986: 109.6, 1987: 113.6,
    1988: 118.3, 1989: 124, 1990: 130.7, 1991: 136.2, 1992: 140.3,
    1993: 144.5, 1994: 148.2, 1995: 152.4, 1996: 156.9, 1997: 160.5,
    1998: 163, 1999: 166.6, 2000: 172.2, 2001: 177.1, 2002: 179.9,
    2003: 184, 2004: 188.9, 2005: 195.3, 2006: 201.6, 2007: 207.3,
    2008: 215.3, 2009: 214.5, 2010: 218.1, 2011: 224.9, 2012: 229.6,
    2013: 233, 2014: 236.7, 2015: 237, 2016: 240, 2017: 245.1,
    2018: 251.1, 2019: 255.7, 2020: 258.8, 2021: 271, 2022: 292.7,
    2023: 304.7, 2024: 313.7, 2025: 322.3
}


def calcBenefits(index_year:int, inc_str:list, birth_year:int, retirement_year:int, death_year:int, woman:bool):

    #for counterfactuals, make changes below as to what amendment versions are active when
    year_stream = []
    benefit_stream=[]
    unindexedBenefitStream = []
    for year in range(retirement_year, death_year +1):
        #only the functions below are the ones currently updated!!!
        benefit=0
        if year>=1939 and year < 1951:
            if q1939(i1939(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=b1939(inc_str, inc_str, index_year, birth_year, retirement_year,year, woman)
            else:
                benefit = 0
        elif year>=1951 and year < 1953:
            if q1950(i1950(inc_str, index_year,retirement_year), inc_str, index_year, birth_year,retirement_year, woman):
                benefit=b1950(inc_str, inc_str,index_year, birth_year, retirement_year, year, woman)
            else:
                benefit = 0
        elif year >=1953 and year < 1955:
            if q1952(i1952(inc_str, index_year,retirement_year), inc_str,index_year, birth_year, retirement_year, woman):
                benefit=b1952(inc_str,inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                benefit = 0
        elif year>=1955 and year <= 1956:
            if q1954(i1954(inc_str, index_year,retirement_year),inc_str, index_year, birth_year,retirement_year, woman):
                benefit=b1954(inc_str,inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                print("hello")
                benefit = 0
        elif year>1956 and year < 1959:
            if q1956(i1956(inc_str, index_year,retirement_year), inc_str,index_year, birth_year,retirement_year, woman):
                benefit=b1956(inc_str,inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                benefit = 0
        elif year>=1959 and year < 1961:
            if q1958(i1958(inc_str, index_year,retirement_year),inc_str, index_year, birth_year,retirement_year, woman):
                benefit=b1958(inc_str,inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                benefit = 0
        elif year == 1961:
            if q1960(i1960(inc_str, index_year,retirement_year), inc_str, index_year, birth_year, retirement_year,woman):
                benefit=b1960(inc_str, inc_str, index_year, birth_year, retirement_year, year,  woman)
            else:
                benefit = 0
        elif year >= 1962 and year < 1965:
            if q1961(i1961(inc_str, index_year,retirement_year), inc_str, index_year, birth_year,retirement_year, woman):
                benefit = b1961(inc_str, inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                benefit = 0
        elif year>=1965 and year <= 1968:
            if q1965(i1965(inc_str, index_year,retirement_year), inc_str, index_year, birth_year, retirement_year,woman):
                benefit=b1965(inc_str, inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                benefit =0
        elif year>=1969 and year < 1970:#Birthdays changed to January 2, 1967 becomes active Febuary 1968, so 1969 for our calculations.
            if q1967(i1967(inc_str, index_year,retirement_year), inc_str, index_year, birth_year, retirement_year,woman):
                benefit=b1967(inc_str, inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                benefit = 0
        elif year>=1970 and year < 1971:
            if q1969(i1969(inc_str, index_year,retirement_year), inc_str, index_year, birth_year, retirement_year,woman):
                benefit=b1969(inc_str, inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                benefit = 0
        elif year>=1971 and year < 1973:
            if q1971(i1971(inc_str, index_year,retirement_year), inc_str, index_year, birth_year, retirement_year,woman):
                benefit=b1971(inc_str, inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                benefit = 0
        elif year>=1973 and year < 1975:
            if q1972(i1972(inc_str, index_year,retirement_year), inc_str, index_year, birth_year, retirement_year,woman, False):
                benefit=b1972(inc_str, inc_str, index_year, birth_year, retirement_year, year, woman)
            else:
                benefit = 0
        elif year>=1975 and year < 1978: #year < 1982:
            if q1973(i1973(inc_str, index_year,retirement_year), inc_str, index_year, birth_year, retirement_year,woman, False):
                    benefit=b1973(inc_str, inc_str, index_year, birth_year, retirement_year, year,  woman) 
            else:
                benefit = 0
        elif year >= 1978: #>= 1982: #modern amendments go into effect for cohort year 1917 and onwards, so this code is technically wrong for people not retiring at the normal retirement age
            if birth_year<1917:
                if q1973(i1973(inc_str, index_year,retirement_year), inc_str, index_year, birth_year, retirement_year,woman, False):
                    benefit=b1973(inc_str, inc_str, index_year, birth_year, retirement_year, year, woman) 
                else:
                    benefit = 0
            else:               
                if qmodern(i_modern(inc_str, index_year, retirement_year), inc_str, index_year, birth_year , retirement_year,woman):
                    benefit=b_modern(inc_str, inc_str, index_year, birth_year, retirement_year, year, woman) #?
                else:
                    benefit = 0
                leg = "modern"
        benefit_stream.append(benefit)
    return benefit_stream
        
def calcSpousalBenefits(inc_str:list, index_year:int, birth_year:int, retirement_year:int, death_year:int, woman:bool, spouse_inc_str:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_death_year:int, spouse_woman:bool ):

    #for counterfactuals, make changes below as to what amendment versions are active when
    year_stream = []
    benefit_stream=[]
    unindexedBenefitStream = []
    for year in range(retirement_year, death_year +1):
        #only the functions below are the ones currently updated!!!
        benefit=0
        if year>=1939 and year < 1951:
            if q1939(i1939(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1939(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year>=1951 and year < 1953:
            if q1950(i1950(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1950(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year >=1953 and year < 1955:
            if q1952(i1952(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1952(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year>=1955 and year < 1956:
            if q1954(i1954(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1954(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year>=1956 and year < 1959:
            if q1956(i1956(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1956(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year>=1959 and year < 1961:
            if q1958(i1958(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1958(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year == 1961:
            if q1960(i1960(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1960(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year >= 1962 and year < 1965:
            if q1961(i1961(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit = spouse1961(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year>=1965 and year <= 1968:
            if q1965(i1965(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1965(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit =0
        elif year>=1969 and year < 1970:
            if q1967(i1967(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman): #Birthdays changed to January 2, 1967 becomes active Febuary 1968, so 1969 for our calculations.
                benefit=spouse1967(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year>=1970 and year < 1971:
            if q1969(i1969(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1969(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year>=1971 and year < 1973:
            if q1971(i1972(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1971(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year>=1973 and year < 1975:
            if q1972(i1972(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=spouse1972(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman)
            else:
                benefit = 0
        elif year>=1975 and year < 1978: #year < 1982:
            if q1973(i1973(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                    benefit=spouse1973(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman) 
            else:
                benefit = 0
        elif year >= 1978: #>= 1982: #modern amendments go into effect for cohort year 1917 and onwards, so this code is technically wrong for people not retiring at the normal retirement age
            if birth_year<1917:
                if q1973(i1973(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year, woman):
                    benefit=spouse1973(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman) 
                else:
                    benefit = 0
            else:          
                if qmodern(i_modern(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year, woman):
                    benefit=spouse_modern(inc_str, index_year, birth_year, retirement_year, retirement_year, woman, spouse_inc_str, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_retirement_year, spouse_woman) #?
                else:
                    benefit = 0
                leg = "modern"
                
    benefit_stream.append(benefit)
    #print("Here is the year stream: ", year_stream)
    #print("Here is the unindexed Benefit Stream: ", unindexedBenefitStream)
    return benefit_stream

def calcWidowBenefits(inc_str:list, index_year:int, birth_year:int, retirement_year:int, death_year:int, woman:bool):

    #for counterfactuals, make changes below as to what amendment versions are active when
    year_stream = []
    benefit_stream=[]
    unindexedBenefitStream = []
    for year in range(retirement_year, death_year +1):
        #only the functions below are the ones currently updated!!!
        benefit=0
        if year>=1939 and year < 1951:
            if q1939(i1939(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1939(inc_str,index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year>=1951 and year < 1953:
            if q1950(i1950(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1950(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year >=1953 and year < 1954:
            if q1952(i1952(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1952(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year>=1954 and year < 1956:
            if q1954(i1954(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1954(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year>=1956 and year < 1959:
            if q1956(i1956(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=widow1956(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year>=1959 and year < 1961:
            if q1958(i1958(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1958(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year == 1961:
            if q1960(i1960(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1960(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year >= 1962 and year < 1965:
            if q1961(i1961(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit = widow1961(inc_str, index_year, birth_year, retirement_year, retirement_year,death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year>=1965 and year <= 1967:
            if q1965(i1965(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1965(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit =0
        elif year>=1968 and year < 1970:
            if q1967(i1967(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1967(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year>=1970 and year < 1971:
            if q1969(i1969(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1969(inc_str, index_year, birth_year, retirement_year, retirement_year,death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year>=1971 and year < 1973:
            if q1971(i1972(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1971(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year>=1973 and year < 1975:
            if q1972(i1972(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                benefit=widow1972(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman)
            else:
                benefit = 0
        elif year>=1975 and year < 1978: #year < 1982:
            if q1973(i1973(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year,woman):
                    benefit=widow1973(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman) 
            else:
                benefit = 0
        elif year >= 1978: #>= 1982: #modern amendments go into effect for cohort year 1917 and onwards, so this code is technically wrong for people not retiring at the normal retirement age
            if birth_year<1917:
                if q1973(i1973(inc_str, index_year, retirement_year), index_year, birth_year, retirement_year,woman):
                    benefit=widow1973(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman) 
                else:
                    benefit = 0
            else:          
                if qmodern(i_modern(inc_str, index_year, retirement_year), index_year, birth_year,retirement_year,woman):
                    benefit=widow_modern(inc_str, index_year, birth_year, retirement_year, retirement_year, death_year, woman, [0]*len(inc_str), index_year, birth_year, retirement_year, retirement_year, not woman) #?
                else:
                    benefit = 0
                leg = "modern"
                
    benefit_stream.append(benefit)
    #print("Here is the year stream: ", year_stream)
    #print("Here is the unindexed Benefit Stream: ", unindexedBenefitStream)
    return benefit_stream

def calcMaximumFamilyBenefits(inc_str:list, index_year:int, birth_year:int, retirement_year:int, death_year:int, woman:bool):
    #for counterfactuals, make changes below as to what amendment versions are active when
    year_stream = []
    benefit_stream=[]
    unindexedBenefitStream = []
    for year in range(retirement_year, death_year +1):
        #only the functions below are the ones currently updated!!!
        benefit=0
        if year>=1939 and year < 1951:
            if q1939(i1939(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=MFB1939(inc_str, index_year, birth_year, retirement_year,year, death_year,woman)
            else:
                benefit = 0
        elif year>=1951 and year < 1953:
            if q1950(i1950(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit=MFB1950(inc_str, index_year, birth_year, retirement_year, year, death_year,woman)
            else:
                benefit = 0
        elif year >=1953 and year < 1955:
            if q1952(i1952(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=MFB1952(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit = 0
        elif year>=1955 and year <= 1956:
            if q1954(i1954(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit=MFB1954(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit = 0
        elif year>1956 and year < 1959:
            if q1956(i1956(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit=MFB1956(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit = 0
        elif year>=1959 and year < 1961:
            if q1958(i1958(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit=MFB1958(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit = 0
        elif year == 1961:
            if q1960(i1960(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=MFB1960(inc_str, index_year, birth_year, retirement_year, year, death_year, woman)
            else:
                benefit = 0
        elif year >= 1962 and year < 1965:
            if q1961(i1961(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit = MFB1961(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit = 0
        elif year>=1965 and year <= 1968:
            if q1965(i1965(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=MFB1965(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit =0
        elif year>=1969 and year < 1970:#Birthdays changed to January 2, 1967 becomes active Febuary 1968, so 1969 for our calculations.
            if q1967(i1967(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=MFB1967(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit = 0
        elif year>=1970 and year < 1971:
            if q1969(i1969(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=MFB1969(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit = 0
        elif year>=1971 and year < 1973:
            if q1971(i1971(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=MFB1971(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit = 0
        elif year>=1973 and year < 1975:
            if q1972(i1972(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=MFB1972(inc_str, index_year, birth_year, retirement_year, year,death_year, woman)
            else:
                benefit = 0
        elif year>=1975 and year < 1978: #year < 1982:
            if q1973(i1973(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                    benefit=MFB1973(inc_str, index_year, birth_year, retirement_year, year,death_year, woman) 
            else:
                benefit = 0
        elif year >= 1978: #>= 1982: #modern amendments go into effect for cohort year 1917 and onwards, so this code is technically wrong for people not retiring at the normal retirement age
            if birth_year<1917:
                if q1973(i1973(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                    benefit=MFB1973(inc_str, index_year, birth_year, retirement_year, year, death_year, woman) 
                else:
                    benefit = 0
            else:               
                if qmodern(i_modern(inc_str, index_year, retirement_year), index_year, birth_year , retirement_year,woman):
                    benefit=MFB_modern(inc_str, index_year, birth_year, retirement_year, year, death_year, woman) #?
                else:
                    benefit = 0
                leg = "modern"
                
    benefit_stream.append(benefit)
    return benefit_stream

def calcChildsBenefit(inc_str:list, index_year:int, birth_year:int, retirement_year:int, death_year:int, woman:bool, child_birth_year:int):
    #for counterfactuals, make changes below as to what amendment versions are active when
    year_stream = []
    benefit_stream=[]
    unindexedBenefitStream = []
    for year in range(retirement_year, retirement_year +1):
        #only the functions below are the ones currently updated!!!
        benefit=0
        if year>=1939 and year < 1951:
            if q1939(i1939(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=children1939(inc_str, index_year, birth_year, retirement_year,year, death_year,woman, child_birth_year)
            else:
                benefit = 0
        elif year>=1951 and year < 1953:
            if q1950(i1950(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit=children1950(inc_str, index_year, birth_year, retirement_year,year, death_year,woman, child_birth_year)
            else:
                benefit = 0
        elif year >=1953 and year < 1955:
            if q1952(i1952(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year, woman):
                benefit=children1952(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year>=1955 and year <= 1956:
            if q1954(i1954(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit=children1954(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year>1956 and year < 1959:
            if q1956(i1956(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit=children1956(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year>=1959 and year < 1961:
            if q1958(i1958(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit=children1958(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year == 1961:
            if q1960(i1960(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=children1960(inc_str, index_year, birth_year, retirement_year, year, death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year >= 1962 and year < 1965:
            if q1961(i1961(inc_str, index_year,retirement_year), index_year, birth_year,retirement_year, woman):
                benefit = children1961(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year>=1965 and year <= 1968:
            if q1965(i1965(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=children1965(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit =0
        elif year>=1969 and year < 1970:#Birthdays changed to January 2, 1967 becomes active Febuary 1968, so 1969 for our calculations.
            if q1967(i1967(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=children1967(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year>=1970 and year < 1971:
            if q1969(i1969(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=children1969(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year>=1971 and year < 1973:
            if q1971(i1971(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=children1971(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year>=1973 and year < 1975:
            if q1972(i1972(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                benefit=children1972(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year>=1975 and year < 1978: #year < 1982:
            if q1973(i1973(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                    benefit=children1973(inc_str, index_year, birth_year, retirement_year, year,death_year, woman, child_birth_year)
            else:
                benefit = 0
        elif year >= 1978: #>= 1982: #modern amendments go into effect for cohort year 1917 and onwards, so this code is technically wrong for people not retiring at the normal retirement age
            if birth_year<1917:
                if q1973(i1973(inc_str, index_year,retirement_year), index_year, birth_year, retirement_year,woman):
                    benefit=children1973(inc_str, index_year, birth_year, retirement_year, year, death_year, woman, child_birth_year) 
                else:
                    benefit = 0
            else:               
                if qmodern(i_modern(inc_str, index_year, retirement_year), index_year, birth_year , retirement_year,woman):
                    benefit=children_modern(inc_str, index_year, birth_year, retirement_year, year, death_year, woman, child_birth_year)
                else:
                    benefit = 0
                leg = "modern"
                
    benefit_stream.append(benefit)
    return benefit_stream



test_stream=[1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,
            1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,
            1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000,1000000]


cohort_year=1900

index_year = cohort_year+22 #I can prob try to check some of the oddities where before 22 stuff applies
retirement_year=cohort_year+65
death_year=retirement_year+10
woman=False
test_stream=test_stream[0:retirement_year-index_year]

#print(retirement_year)

# print(i1971(test_stream, index_year))

#print(calcMaximumFamilyBenefits(test_stream, index_year, cohort_year, retirement_year, death_year, woman))
