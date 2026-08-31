#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#Daniel Carrillo
#1971 coded legislation

#As a general note, our model operates on a year by year flow of time. The actual Social Security Legislation works on a quarter by quarter flow of time
#This could cause certain distortions. For example, quarters of coverage will probably be overestimated, and periods of unemployment longer than a quarter will not show up in our model
#In our model, all the quarters are scaled to years. For example "the quotient obtained by dividing the total wages paid an individual before the quarter in which he died or became entitled to receive primary insurance benefits"
#Is read as "the quotient obtained by dividing the total wages paid an individual before the YEAR in which he died or became entitled to receive primary insurance benefits"
#As a note, there are no secondary benefits yet, and also maximum benefits have not been coded because those are related to secondary benefits

#also this amendment model currently only works for men, since women have a different retirement age
#We still need to add the drop rule!
#last updated 2/17/25 by DC


# In[17]:

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


#found on pdf page 6 and 7 of 1971 pdf
def i1971(income_stream:list, index_year:int, retirement_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1952 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy()
    for i in range(len(income_stream)):
        if i+index_year<1936:
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
    return adjusted_income_stream

#has not changed since 1960

def a1971(adjusted_income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, death_year = 0):
    """This function returns the average monthly wage (int) of an individual as determined by the 1952 legislation.
        This is more complicated than one might think, which is why it has its own seperate function.
        The inputs are (adjusted_income_stream:list,index_year:int, birth_year:int).
        adjusted_income_stream -- a list of nominal incomes a person received in each year, adjusted by the relevant legislation. i1952 will create the caps for you.
        index_year -- the year in which an individual begins their income_stream   
        birth_year -- the year the individual is born.
        woman -- gender of recipient, True if a woman
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

    elapsed_years=end_year-beginning_year
    
    highest_years=elapsed_years-drops

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
            end_year=birth_year+62 #note that this is different from the previus legislation, "first entitled" now means age 62 in the legislation
        else:
            end_year=birth_year+65
        drops=5
    
        elapsed_years=end_year-beginning_year

        highest_years=elapsed_years-drops
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
    
    return avg_monthly_wage

#see 1961 pdf page 7, has not been updated since then
def q1971(adjusted_income_stream:list, original_income_stream, index_year:int, birth_year:int,  retirement_year:int,  woman:bool, skip1939 = False): #this might not be completely correct/ might be off by half a year
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
    startIndex = max(0, 1950-index_year)
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


    reference_year=max(1951,birth_year+21) #odd nuance of the legislation
    if coverage_quarters>40:
        return True
    elif ((coverage_quarters)>=((4/4)*(end_year)-reference_year)) and (coverage_quarters>=6):
        return True
    else:
        return False
    
def qcurrent1971(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
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

#see pdf page 2 and 3 of 1971 version
def bb1971(income_stream:list,original_income_stream:list,  avg_monthly_wage:float, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function takes an average monthly wage and calculates the nominal monthly benefit (int) under the 1950 legislation.
        The inputs are (avg_monthly_wage:int, index_year:int, birth_year:int)
        avg_monthly_wage -- the average monthly wage a person received throughout their working history as determined by the 1950 legislation. a1950 will create this value for you.
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
        woman -- gender of recipient, True if a woman
    """
    #retirement_year=index_year+len(income_stream)
    #adjusted_income_stream=i1971(income_stream, index_year)
    #avg_monthly_wage=a1971(adjusted_income_stream, index_year, birth_year, woman)
    #initialize variables
    startIndex = max(0, 1950-index_year)
    adjusted_income_stream = income_stream[startIndex: ]

    
    if (birth_year+65<1950): #this checks if they are old enough to have a pib; someone who did have a pib would receive a new updated pia based on these charts below, if they do they go through the formulas differently. This is what the tables primarily deal with.
        pib=b1939(i1939(original_income_stream, index_year, retirement_year), index_year, index_year, birth_year,retirement_year, reference_year, woman)
    elif (birth_year+65<1971):
        pia_1969=b1969(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    
    

    pib_list = [
        [0, 16.20], [16.21, 16.84],[16.85, 17.60],[17.61, 18.40],[18.41, 19.24],[19.25, 20.00],[20.01, 20.64],[20.65, 21.28],[21.29, 21.88],[21.89, 22.28],
        [22.29, 22.68],[22.69, 23.08],[23.09, 23.44],[23.45, 23.76],[23.77, 24.20],[24.21, 24.60],[24.61, 25.00],[25.01, 25.48],[25.49, 25.92],[25.93, 26.40],
        [26.41, 26.94],[26.95, 27.46],[27.47, 28.00],[28.01, 28.68],[28.69, 29.25],[29.26, 29.68],[29.69, 30.36],[30.37, 30.92],[30.93, 31.36],[31.37, 32.00],
        [32.01, 32.60],[32.61, 33.20],[33.21, 33.88],[33.89, 34.50],[34.51, 35.00],[35.01, 35.80],[35.81, 36.40],[36.41, 37.08],[37.09, 37.60],[37.61, 38.20],
        [38.21, 39.12],[39.13, 39.68],[39.69, 40.33],[40.34, 41.12],[41.13, 41.76],[41.77, 42.44],[42.45, 43.20],[43.21, 43.76],[43.77, 44.44],[44.45, 44.88],
        [44.89, 45.60]
    ]


    pia_1969_list = [64.00, 65.00, 66.40, 67.70, 68.90, 70.30, 71.60, 72.80, 74.20, 75.50, 76.80, 78.00, 79.40, 80.80, 82.30, 83.60, 84.90, 86.40, 87.80, 89.20,90.60, 91.90, 93.30, 94.70, 96.20, 97.50, 98.80, 100.30, 101.70, 103.00,104.50, 105.80, 107.20, 108.60, 110.00, 111.40, 112.70, 114.20, 115.60, 116.90, 118.40, 119.80, 121.00, 122.50, 123.90, 125.30, 126.70, 128.20, 129.50, 130.80, 132.30, 133.70, 134.90, 136.40, 137.80, 139.20, 140.60, 142.00, 143.50, 144.70, 146.20, 147.60, 148.90, 150.40, 151.70, 153.00, 154.50, 155.9, 157.4, 158.60, 160.00, 161.50, 162.80, 164.30, 166.60, 166.90, 168.40, 169.80, 171.30, 172.50, 173.90, 175.40, 176.70, 178.20, 179.40, 180.70, 182, 183.40, 184.60, 185.90, 187.3, 188.50, 189.8, 191.20, 192.4, 193.70, 195, 196.40, 197.60, 198.90, 200.30, 201.50,202.80, 204.20, 205.40, 206.70, 208.00, 209.30, 210.60, 211.90, 213.30, 214.50, 215.80, 217.20, 218.40, 219.70, 220.80, 222, 223.10, 224.30, 225.40, 226.6, 227.70, 228.9, 230.00, 231.2, 232.30, 233.50, 234.60, 235.80, 236.90, 238.10, 239.20, 240.40, 241.50, 242.70, 243.80, 245.00, 246.10, 247.30, 248.40, 249.60, 250.70]


                
    avg_monthly_wage_list = [
        [0, 77], [77, 79], [79, 81], [81, 82], [82, 84], [84, 86], [86, 88], [88, 90], [90, 91],
        [91, 93], [93, 95], [95, 97], [97, 98], [98, 100], [100, 102], [102, 103], [103, 105],
        [105, 107], [107, 108], [108, 110], [110, 114], [114, 119], [119, 123], [123, 128],
        [128, 133], [133, 137], [137, 142], [142, 147], [147, 151], [151, 156], [156, 161],
        [161, 165], [165, 170], [170, 175], [175, 179], [179, 184], [184, 189], [189, 194],
        [194, 198], [198, 203], [203, 208], [208, 212], [212, 217], [217, 222], [222, 226],
        [226, 231], [231, 236], [236, 240], [240, 245], [245, 250], [250, 254], [254, 259],
        [259, 264], [264, 268], [268, 273], [273, 278], [278, 282], [282, 287], [287, 292],
        [292, 296], [296, 301], [301, 306], [306, 310], [310, 315], [315, 320], [320, 324],
        [324, 329], [329, 334], [334, 338], [338, 343], [343, 348], [348, 352], [352, 357], [357, 362],
        [362, 366], [366, 371], [371, 376], [376, 380], [380, 385], [385, 390], [390, 394],
        [394, 399], [399, 404], [404, 408], [408, 413], [413, 418], [418, 422], [422, 427],
        [427, 432], [432, 437], [437, 441], [441, 446], [446, 451], [451, 455], [455, 460],
        [460, 465], [465, 469], [469, 474], [474, 479], [479, 483], [483, 488], [488, 493],
        [493, 497], [497, 502], [502, 507], [507, 511], [511, 516], [516, 521], [521, 525],
        [525, 530], [530, 535], [535, 539], [539, 544], [544, 549], [549, 554], [554, 557],
        [557, 561], [561, 564], [564, 568], [568, 571], [571, 575], [575, 578], [578, 582],
        [582, 585], [585, 589], [589, 592], [592, 596], [596, 599], [599, 603], [603, 606],
        [606, 610], [610, 613], [613, 617], [617, 621], [621, 624], [624, 628], [628, 631],
        [631, 635], [635, 638], [638, 642], [642, 645], [645, 649], [649, 653], [653, 657],
        [657, 661], [661, 666], [666, 671], [671, 676], [676, 681], [681, 686], [686, 691],
        [691, 696], [696, 701], [701, 706], [706, 711], [711, 716], [716, 721], [721, 726],
        [726, 731], [731, 736], [736, 741], [741, 746], [746, 751]
    ]


    
    pia_list=[70.40, 71.50, 73.10, 74.50, 75.80, 77.40, 78.80, 80.10, 81.70, 83.10, 84.50, 85.80, 87.40, 88.90, 90.60, 91.90, 93.40, 95.10, 96.60, 98.20, 99.70,
              101.10, 102.70, 104.20, 105.90, 107.30, 108.70, 110.40, 111.90, 113.30, 115.00, 116.40, 118.00, 119.50, 121.00, 122.60, 124.00, 125.70, 127.20, 
    128.60, 130.30, 131.80, 133.10, 134.80, 136.30, 137.90, 139.40, 141.10, 142.50, 143.90, 145.60, 147.10, 148.40, 150.10, 151.60, 153.20, 154.70, 156.20,  
    157.90, 159.20, 160.90, 162.40, 163.80, 165.50, 166.90, 168.30, 170.00, 171.50, 173.20, 174.50, 176.00, 177.70, 179.10, 180.80, 182.20, 183.60, 185.30,  
    186.80, 188.50, 189.80, 191.30, 193.00, 194.40, 196.10, 197.40, 198.80, 200.20, 201.80, 203.10, 204.50, 206.10, 207.40, 208.80, 210.40, 211.70, 213.10,  
              214.50, 216.10, 217.40, 218.80, 220.40, 221.70, 223.10, 224.70, 226.00, 227.40, 228.80, 230.3, 231.70, 233.1, 234.70, 236, 237.40, 239, 240.30, 241.7, 242.90,244.2, 245.50, 246.80, 248.00,  
    249.30, 250.50, 251.80, 253.00, 254.40, 255.60, 256.90, 268.10, 259.40, 260.60, 262.00, 263.20, 264.50, 266.70, 267.00, 268.20, 269.50, 270.80, 272.10,  
    273.30, 274.60, 276.80, 276.60, 277.40, 278.40, 279.40, 280.40, 281.40, 282.40, 283.40, 284.40, 285.40, 286.40, 287.40, 288.40, 289.40, 290.40, 291.40, 292.40, 293.40, 294.40, 295.40]


    
    #print(len(pia_list))
    #print(len(avg_monthly_wage_list))


    pia_A=0
    pia_B=0
    pia_C=0

    #actual benefit formula
    if ((q1971(income_stream, original_income_stream, index_year, birth_year,retirement_year, woman, skip1939 = True)==True)): #Check if the worker is fully-insured, as well as to place them in the proper formula
        for i in range(len(avg_monthly_wage_list)):
            #if i >160: break
            if avg_monthly_wage>=avg_monthly_wage_list[i][0] and avg_monthly_wage<avg_monthly_wage_list[i][1]:
                #print("hit! ", avg_monthly_wage_list[i][0], avg_monthly_wage,avg_monthly_wage_list[i][1])
                if i < 160:
                   pia_A=pia_list[i]
                else:
                    pia_A = pia_list[-1]
    elif ((q1971(income_stream, original_income_stream, index_year, birth_year,retirement_year, woman)==True) and (birth_year+65<1950)):
        for i in range(len(pib_list)):
            if pib>=pib_list[i][0] and pib<pib_list[i][1]: 
                pia_B=pia_list[i]
    elif ((q1971(income_stream, original_income_stream, index_year, birth_year, retirement_year,woman, skip1939 = True)==True) and (birth_year+65<=1971)):
        for i in range(len(pia_1969_list)):
            if pia_1969>=pia_1969_list[i][0] and pia_1965<pia_1965_list[i][1]:
                pia_C=pia_list[i]
    #legislation says to take the maximum of these    
    #print("avg: ", avg_monthly_wage)
    pia=max(pia_A, pia_B, pia_C)
    # max_benefit=max(max_benefit_A,max_benefit_B,max_benefit_C)

    #early retirement penalty I still haven't added the work penalty for early retirement

    return pia #, max_benefit



# In[19]:


def b1971(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        woman -- gender of recipient, True if a woman
    """ 
    #retirement_year=index_year+len(income_stream)
    monthly_benefits=0
    adjusted_income_stream=i1971(income_stream, index_year, retirement_year)

    if retirement_year <= 1950: avg_monthly_wage = a1939(i1939(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1952 : avg_monthly_wage = a1950(i1950(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1954: avg_monthly_wage = a1952(i1952(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1956: avg_monthly_wage=a1954(i1954(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1958: avg_monthly_wage = a1956(i1956(original_income_stream, index_year, retirement_year),original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1960: avg_monthly_wage=a1958(i1958(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1961: avg_monthly_wage=a1960(i1960(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1965: avg_monthly_wage=a1961(i1961(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1967: avg_monthly_wage = a1965(i1965(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year, reference_year, woman)
    elif retirement_year <= 1969:  avg_monthly_wage = a1967(i1967(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, reference_year, reference_year, woman)
    elif retirement_year <= 1971: avg_monthly_wage = a1969(i1969(original_income_stream, index_year, retirement_year), original_income_stream,index_year, birth_year, retirement_year, reference_year, woman)
    else: avg_monthly_wage=a1971(adjusted_income_stream, original_income_stream, index_year, birth_year,retirement_year, reference_year, woman)

    nominal_total_contributions=t1971(adjusted_income_stream, index_year)
    monthly_benefits=bb1971(adjusted_income_stream, original_income_stream,avg_monthly_wage, index_year, birth_year, retirement_year, reference_year, woman)

    nra=65
    if (retirement_year-birth_year)<nra:
        early_deduction=12*(5/9 * .01)*(nra-(retirement_year-birth_year))
        monthly_benefits=(1-early_deduction)*monthly_benefits
    return round(monthly_benefits,1)
    
# pdf page 7-8 of 1971 pdf 
def t1971(income_stream:list, index_year:int):
    
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]

    adjusted_income_stream=i1971(income_stream, index_year, index_year+len(income_stream)) #to apply the taxable maximums to the benefit stream
    
    for i in range(len(income_stream)): 
        if (i+index_year) <1937:
             employee_tax_rate= 0.00
             employer_tax_rate= 0.00
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate) 
        if (i+index_year) <= 1949 and (i+index_year>=1937): #actual tax rates
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
             employee_tax_rate= 0.0225
             employer_tax_rate= 0.0225
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) == 1959 :
             employee_tax_rate= 0.025
             employer_tax_rate= 0.025
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <= 1961 and (index_year+i)>=1960:
             employee_tax_rate= 0.03
             employer_tax_rate= 0.03
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) == 1962: 
             employee_tax_rate= 0.03125
             employer_tax_rate= 0.03125
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) <=1965 and (index_year+i) >=1963: 
             employee_tax_rate= 0.03625
             employer_tax_rate= 0.03625
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) ==1966: 
             employee_tax_rate= 0.0385
             employer_tax_rate= 0.0385
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1967 and (index_year+i) <=1967: 
             employee_tax_rate= 0.039
             employer_tax_rate= 0.039
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1968 and (index_year+i) <=1968: 
             employee_tax_rate= 0.038
             employer_tax_rate= 0.038
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1969 and (index_year+i) <=1970: 
             employee_tax_rate= 0.042
             employer_tax_rate= 0.042
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1971 and (index_year+i) <=1972: 
             employee_tax_rate= 0.046
             employer_tax_rate= 0.046
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1973 and (index_year+i) <=1975: 
             employee_tax_rate= 0.05
             employer_tax_rate= 0.05
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (index_year+i) >=1975: 
             employee_tax_rate= 0.0515
             employer_tax_rate= 0.0515
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)

            
    return nominal_contributions


def death1971(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    woman: This is TRUE if the deceased was female.
    '''
    if (q1971(income_stream, index_year, birth_year, retirement_year,woman)): 
        monthlyBenefits = b1971(income_stream, index_year, birth_year, retirement_year, woman)
        return max(3 * monthlyBenefits, 255)
    else:
        return 0
    

def spouse1971(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
        This code assumes that the male is "financially dependent" on the wife for spousal benefit calculation
    """ 

    spousal_benefit = 0
    
    if q1971(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_woman):
        spouse_benefit = b1971(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
    else: spouse_benefit = 0
    primary_adjusted_income_stream=i1971(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1971(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1971(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)
    

    deduction = 1

    if spouse_birth_year + 65 > spouse_retirement_year:
        deduction = deduction - (25/36) * 0.01 * 12 *(spouse_birth_year+65 - spouse_retirement_year)

    spouse_benefit_guarantee = 0.5*primary_PIA *deduction
    spousal_benefit = 0
    if spouse_benefit < spouse_benefit_guarantee:
        spousal_benefit = spouse_benefit_guarantee - spouse_benefit
        
    return round(spousal_benefit,1)

def widow1971(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if ((retirement_year >= widow_birth_year +62) or (widow_woman == True and retirement_year >= widow_birth_year +60)) and q1971(income_stream,index_year,birth_year, retirement_year, woman):
        widowMonthlyBenefit = b1971(widow_income_stream, widow_index_year, widow_birth_year,widow_retirement_year, widow_reference_year,widow_woman)
        adjusted_income_stream=i1971(income_stream, index_year, retirement_year)
        avg_monthly_wage = a1971(adjusted_income_stream, index_year, birth_year, retirement_year, reference_year, woman, death_year)
        primaryPIA = bb1971(income_stream,avg_monthly_wage, index_year, birth_year,retirement_year,reference_year ,woman)
        

        deduction = 1
        if (widow_woman == True and retirement_year <= widow_birth_year + 62):
            deduction -= (5/9) * 0.01 * 12 * (widow_birth_year + 62 - retirement_year)

        widow_benefit_guarantee = 0.825*primaryPIA  * deduction

        widow_benefit = 0
        if widowMonthlyBenefit < widow_benefit_guarantee:
            widow_benefit = widow_benefit_guarantee - widowMonthlyBenefit

        return math.ceil(widow_benefit * 10) / 10.0
    else:
        return 0
    
def MFB1971(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1967(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1967(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    
    primary_avg_monthly_wage = math.floor(primary_avg_monthly_wage)
    
    avg_monthly_wage_list = [
        [0, 77], [77, 79], [79, 81], [81, 82], [82, 84], [84, 86], [86, 88], [88, 90], [90, 91],
        [91, 93], [93, 95], [95, 97], [97, 98], [98, 100], [100, 102], [102, 103], [103, 105],
        [105, 107], [107, 108], [108, 110], [110, 114], [114, 119], [119, 123], [123, 128],
        [128, 133], [133, 137], [137, 142], [142, 147], [147, 151], [151, 156], [156, 161],
        [161, 165], [165, 170], [170, 175], [175, 179], [179, 184], [184, 189], [189, 194],
        [194, 198], [198, 203], [203, 208], [208, 212], [212, 217], [217, 222], [222, 226],
        [226, 231], [231, 236], [236, 240], [240, 245], [245, 250], [250, 254], [254, 259],
        [259, 264], [264, 268], [268, 273], [273, 278], [278, 282], [282, 287], [287, 292],
        [292, 296], [296, 301], [301, 306], [306, 310], [310, 315], [315, 320], [320, 324],
        [324, 329], [329, 334], [334, 338], [338, 343], [343, 348], [348, 352], [352, 357], [357, 362],
        [362, 366], [366, 371], [371, 376], [376, 380], [380, 385], [385, 390], [390, 394],
        [394, 399], [399, 404], [404, 408], [408, 413], [413, 418], [418, 422], [422, 427],
        [427, 432], [432, 437], [437, 441], [441, 446], [446, 451], [451, 455], [455, 460],
        [460, 465], [465, 469], [469, 474], [474, 479], [479, 483], [483, 488], [488, 493],
        [493, 497], [497, 502], [502, 507], [507, 511], [511, 516], [516, 521], [521, 525],
        [525, 530], [530, 535], [535, 539], [539, 544], [544, 549], [549, 554], [554, 557],
        [557, 561], [561, 564], [564, 568], [568, 571], [571, 575], [575, 578], [578, 582],
        [582, 585], [585, 589], [589, 592], [592, 596], [596, 599], [599, 603], [603, 606],
        [606, 610], [610, 613], [613, 617], [617, 621], [621, 624], [624, 628], [628, 631],
        [631, 635], [635, 638], [638, 642], [642, 645], [645, 649], [649, 653], [653, 657],
        [657, 661], [661, 666], [666, 671], [671, 676], [676, 681], [681, 686], [686, 691],
        [691, 696], [696, 701], [701, 706], [706, 711], [711, 716], [716, 721], [721, 726],
        [726, 731], [731, 736], [736, 741], [741, 746], [746, 751]
    ]

    maximum_family_benefits = [105.6, 107.3, 109.7, 111.8, 113.7, 116.4, 118.2, 120.2, 122.6, 124.7,
    126.8, 128.7, 131.1, 133.4, 135.9, 137.9, 140.1, 142.7, 144.0, 147.3,
    149.6, 151.7, 154.1, 156.3, 158.9, 161.0, 163.1, 165.6, 167.9, 170.0,
    172.5, 174.6, 177.0, 179.3, 181.5, 183.9, 186.0, 188.0, 190.8, 192.9,
    195.5, 197.7, 199.7, 202.2, 204.5, 206.9, 209.1, 211.7, 214.8, 219.2,
    222.7, 227.1, 231.5, 235.0, 239.4, 243.8, 247.3, 251.7, 256.1, 259.6,
    264.0, 268.4, 272.0, 276.4, 280.8, 284.3, 288.7, 293.1, 296.6, 301.0,
    305.4, 308.9, 313.3, 317.7, 321.2, 325.6, 330.0, 333.6, 338.0, 342.4,
    345.9, 350.3, 354.7, 358.2, 362.6, 367.0, 370.5, 374.9, 379.3, 383.7, 385.5,
    387.7, 389.9, 391.6, 393.8, 396.0, 397.8, 400.0, 402.2, 404.0, 406.2,
    408.4, 410.1, 412.3, 414.5, 416.3, 418.8, 420.7, 422.4, 424.6, 426.8,
    428.6, 430.8, 433.0, 435.2, 436.5, 438.3, 439.6, 441.4, 442.7, 444.4,
    445.8, 447.5, 448.8, 450.6, 451.9, 453.7, 455.0, 456.8, 458.1, 459.8,
    461.2, 462.9, 464.7, 466.0, 467.8, 469.4, 471.7, 473.9, 476.2, 478.3,
    480.6, 482.7, 484.1, 485.5, 487.2, 489.0, 490.7, 492.5, 494.2, 496.0,
    497.7, 499.5, 501.2, 503.0, 504.7, 506.5, 508.2, 510.0, 511.7, 513.5,
    515.2, 517.0
    ]


    for i in range(len(avg_monthly_wage_list)):
        #print(avg_monthly_wage_list[i][0], avg_monthly_wage_list[i][1], maximum_family_benefits[i] )
        if primary_avg_monthly_wage>=avg_monthly_wage_list[i][0] and primary_avg_monthly_wage<avg_monthly_wage_list[i][1]: 
            maximum_family_benefit=maximum_family_benefits[i]


    if maximum_family_benefit: return maximum_family_benefit
    else: return 0

def children1971(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
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
    primary_adjusted_income_stream=i1971(income_stream, index_year, retirement_year)
    if reference_year < death_year:
        primary_avg_monthly_wage = a1971(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    else:
        primary_avg_monthly_wage = a1971(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman, death_year)    
    primary_PIA = bb1971(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)

    if reference_year >= death_year: #If the primary is dead
        return math.ceil(0.75*primary_PIA*10)/10
    else: 
        return math.ceil(0.5* primary_PIA*10)/10