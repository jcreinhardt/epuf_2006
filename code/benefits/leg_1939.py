#iYEAR, aYEAR, qYEAR, and bbYEAR are all intermediate functions that are called within the main output functions in the next cell
import math
#this function puts the taxable maximums on the income stream; it can be found on page 14 of 1939 pdf.
def i1939(income_stream:list, index_year:int, retirement_year:int):
    """This function applies the taxable maximum caps to an income stream, as set in the 1939 legislation.
        This function returns the information as a list.
        The inputs are (income_stream:list,index_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
    """
    adjusted_income_stream=income_stream.copy()
    for i in range(len(income_stream)):
        if i+index_year<=1936:
            adjusted_income_stream[i]=0
        if income_stream[i]>3000 and i+index_year>1936:
            adjusted_income_stream[i]=3000
            
    return adjusted_income_stream


#this function calculates average monthly wage (for the purposes of SSec legislation) from an income stream; it can be found on page 17 of the pdf page 17, section (f) 
#this assumes that people retire at 65, which was the full retirement year at this point
# Sec. 209 (f) https://www.ssa.gov/history/pdf/Downey%20PDFs/Social%20Security%20Amendments%20of%201939.pdf#page=1116
def a1939(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
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
    
    for i in range(len(adjusted_income_stream)):
        if (i+index_year>1936) and not (i+index_year-22<0 and adjusted_income_stream[i]<200): #there's something else here, check @Daniel
            count+=1
            total_wage+=adjusted_income_stream[i]
    if count==0:
        avg_monthly_wage=0
    else: 
        avg_monthly_wage=total_wage/(count*12)
    avg_monthly_wage=int(avg_monthly_wage)
    # print("avg: ", avg_monthly_wage)
    return avg_monthly_wage

#qualification rules, pdf page 17
#this is for people who are considered "fully insured individuals"; "currently insured individuals" is a different category see page 18 of the pdf
#also assuming that people retire at 65
#pay attention to what a "quarter of coverage" is defined as. This can be found on the top of page 18 of the 1939 pdf
#There's an odd rule here at the top of page 18 when wages hit 3k in a calendar year, as of 1/26/25, it is not relevant to our model
def q1939(income_stream:list, index_year:int, birth_year:int, retirement_year:int, woman:bool): 
    """This function determines whether an individual is considered fully-insured as of the 1939 legislation.
        This function returns a boolean.
        The inputs are (adjusted_income_stream:list, index_year:int, birth_year:int)
        income_stream -- a list of nominal incomes a person received in each year
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born.
    """
    #adjusted_income_stream=i1939(income_stream, index_year, retirement_year)
    coverage_quarters=0 #we are going to assume that one year of coverage equals 4 coverage quarters
    startIndex = max(0, 1937-index_year)
    for i in range(startIndex, len(income_stream)):
        if income_stream[i]>=200:
            coverage_quarters+=4
        elif income_stream[i] >=150:
            coverage_quarters +=3
        elif income_stream[i] >=100:
            coverage_quarters +=2
        elif income_stream[i] >=100:
            coverage_quarters +=1
    
    coverage_quarters_in_elapsed_years = 0
    end_year = birth_year + 65
    if index_year <= end_year:
        for i in range(startIndex, min(len(income_stream), end_year - index_year+1)): #only consider income until the individual turns 65. The minimum is necessary if the person stops working before 65.
            if income_stream[i]>=200:
                coverage_quarters_in_elapsed_years+=4
            elif income_stream[i] >=150:
                coverage_quarters_in_elapsed_years +=3
            elif income_stream[i] >=100:
                coverage_quarters_in_elapsed_years +=2
            elif income_stream[i] >=100:
                coverage_quarters_in_elapsed_years +=1

    reference_year=max(1936,birth_year+21) 
    #print("quarters needed: ",2* ((birth_year+65)-reference_year))
    #odd nuance of the legislation

    if coverage_quarters>40:
        return True
    elif (2*(coverage_quarters_in_elapsed_years/4)>=(birth_year+65)-reference_year) and (coverage_quarters_in_elapsed_years>=6):
        return True
    else:
        return False

def qcurrent1939(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, death_year:int, woman:bool): 
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



#benefit rules, pdf page 17
#Sec. 209 (e) https://www.ssa.gov/history/pdf/Downey%20PDFs/Social%20Security%20Amendments%20of%201939.pdf#page=1101
def bb1939(income_stream:list, original_income_stream:list, avg_monthly_wage:float, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function takes an average monthly wage and calculates the nominal monthly benefit (int) under the 1939 legislation.
        The inputs are (avg_monthly_wage:int, index_year:int, birth_year:int)
        income_stream -- a list of nominal incomes a person received in each year
        index_year -- the year in which an individual begins their income_stream    
        birth_year -- the year the individual is born
    """ 
    #avg_monthly_wage=a1939(income_stream, index_year, birth_year, retirement_year)
    #adjusted_income_stream=i1939(income_stream, index_year)
    adjusted_income_stream = income_stream    

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
    

#Sec. 209 (e) (2)
def b1939(income_stream:list, original_income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1939 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """   
    monthly_benefits=0
    #retirement_year = index_year+len(income_stream)
    retirement_age=retirement_year-birth_year
    adjusted_income_stream = i1939(income_stream, index_year, retirement_year)
    avg_monthly_wage=a1939(adjusted_income_stream, original_income_stream, index_year, birth_year, retirement_year, reference_year, woman)
    
    #print("retirement age: ", q1939(income_stream, index_year, birth_year))
    #print("here!")
    #print(q1939(income_stream, index_year, birth_year))
    if q1939(adjusted_income_stream, index_year, birth_year,retirement_year, woman)==True and retirement_age>=65:
        #print("we're here")
        monthly_benefits=bb1939(adjusted_income_stream, original_income_stream, avg_monthly_wage,index_year,birth_year, retirement_year, reference_year, woman)
    
    return  math.trunc(monthly_benefits*100) /100

#Sec. 1400, 1410 
def t1939(income_stream:list, index_year:int):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1939 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
    """ 
    employee_tax_rate = 0
    employer_tax_rate = 0
    nominal_contributions=[]
    adjusted_income_stream=i1939(income_stream,index_year)
    
    for i in range(len(adjusted_income_stream)):
        if (i+index_year) <1937:
             employee_tax_rate= 0.01
             employer_tax_rate= 0.01
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1942 and (i+index_year) >=1937:
             employee_tax_rate= 0.01
             employer_tax_rate= 0.01
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1945 & (i+index_year) >=1943:
             employee_tax_rate= 0.02
             employer_tax_rate= 0.02
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) <= 1948 & (i+index_year) >=1946:
             employee_tax_rate= 0.025
             employer_tax_rate= 0.025
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
        if (i+index_year) >=1949:
             employee_tax_rate= 0.03
             employer_tax_rate= 0.03
             nominal_contributions.append(adjusted_income_stream[i]*employee_tax_rate)
            
    return nominal_contributions


def death1939(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, survivors:bool):
    '''
    income_stream: The income stream after 1936. This code assumes that all earnings are after 1936, as previous earnings would not be considered.
    index_year: the year in which the individual recieved their first wage
    retirement_year: the year in which the individual retired
    death_year: the year in which the individual died
    survivors: this boolean variable is TRUE if the deceased is survived by a widow, child, or parent that qualifies for monthly survivor benefits (if anyone recieves survivor's benefits on the deceased's record)
    '''
    if (q1939(income_stream, index_year, birth_year, retirement_year,woman) and not survivors): 
        monthlyBenefits = b1939(income_stream, index_year, birth_year, retirement_year, reference_year, woman)
        return 6 * monthlyBenefits
    else:
        return 0
    
def spouse1939(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int, woman:bool, spouse_income_stream:list, spouse_index_year:int, spouse_birth_year:int, spouse_retirement_year:int, spouse_reference_year:int, spouse_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the 1950 legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        Reference year -- what years dollars you want the output to be in
    """ 
    
    if spouse_woman == True and woman == False:
        spousal_benefit = 0
        if q1939(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_woman):
            spouse_benefit = b1939(spouse_income_stream, spouse_index_year, spouse_birth_year, spouse_retirement_year, spouse_reference_year,spouse_woman)
        else: spouse_benefit = 0
        primary_adjusted_income_stream=i1939(income_stream, index_year, retirement_year)
        primary_avg_monthly_wage = a1939(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
        primary_PIA = bb1939(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)

        spouse_benefit_guarantee = 0.5*primary_PIA 

        spousal_benefit = 0
        if spouse_benefit < spouse_benefit_guarantee:
            spousal_benefit = spouse_benefit_guarantee - spouse_benefit

        return spousal_benefit
    else:
        return 0
    
def widow1939(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, widow_income_stream:list, widow_index_year:int, widow_birth_year:int, widow_retirement_year:int, widow_reference_year:int, widow_woman:bool):
    """This function outputs the nominal monthly benefit (int) an individual would have received under the relevant legislation. 
        The function inputs are (income_stream:list, index_year:int, birth_year:int).
        income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """ 
    if widow_woman == True and widow_retirement_year >= widow_birth_year + 65 and q1939(income_stream,index_year,birth_year, retirement_year,woman):
        spousal_benefit = 0
        primary_adjusted_income_stream=i1939(income_stream, index_year, retirement_year)
        primary_avg_monthly_wage = a1939(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
        spouseMonthlyBenefit = b1939(widow_income_stream, widow_index_year, widow_birth_year, widow_retirement_year, widow_reference_year, widow_woman)
        primaryPIA = bb1939(income_stream, primary_avg_monthly_wage, index_year, retirement_year, birth_year,reference_year, woman)


        spouse_benefit_guarantee = 0.75*primaryPIA 

        spousal_benefit = 0
        if spouseMonthlyBenefit < spouse_benefit_guarantee:
            spousal_benefit = spouse_benefit_guarantee - spouseMonthlyBenefit

        return spousal_benefit
    else:
        return 0

def MFB1939(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool):
    """
    This function outputs the Maximum Family Benefit a principal beneficiary would be capped at under the relevant legislation.
     income_stream -- a list of nominal incomes a person received in each year.
        index_year -- the year in which an individual begins their income_stream.
        birth_year -- the year the individual is born.
        death_year -- the year which the primary died
        Reference year -- to which year would the dollars be indexed to. Likely the year in which the entitlement is being paid out.
    """
    primary_adjusted_income_stream=i1939(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1939(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primaryMonthlyBenefit = b1939(primary_adjusted_income_stream, index_year, birth_year, retirement_year, reference_year, woman)

    maximumFamilyBenefit = max(20, min(85, 2*primaryMonthlyBenefit, .8* primary_avg_monthly_wage))
    return maximumFamilyBenefit
    


def children1939(income_stream:list, index_year:int, birth_year:int, retirement_year:int, reference_year:int,death_year:int, woman:bool, child_birth_year:int):
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
    primary_adjusted_income_stream=i1939(income_stream, index_year, retirement_year)
    primary_avg_monthly_wage = a1939(primary_adjusted_income_stream, index_year, birth_year, retirement_year,reference_year, woman)
    primary_PIA = bb1939(income_stream, primary_avg_monthly_wage, index_year, birth_year, retirement_year,reference_year, woman)


    return math.ceil(0.5* primary_PIA *10)/10


