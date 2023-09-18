import numpy as np
import requests
import logging
import math
import pandas as pd
import functions
pd.options.display.float_format = '{:,.2f}'.format

SLOTS_PER_EPOCH = 32
SECONDS_PER_SLOT = 12
BASE_REWARDS_PER_EPOCH = 4
MAX_EFFECTIVE_BALANCE = 2**5 * 10**9
EFFECTIVE_BALANCE_INCREMENT = 2**0 * 10**9
PROPOSER_WEIGHT=8
SYNC_COMMITTEE_SIZE=2**9 # (= 512)	Validators	
EPOCHS_PER_SYNC_COMMITTEE_PERIOD=2**8 # (= 256)	epochs	~27 hours
MAX_VALIDATOR_COUNT = 2**19 # (= 524,288)

states = ['scenario_1', 'scenario_2', 'scenario_3']

## Get current beacon chain data
def get_epoch_data(epoch="latest"):
    try:
        req = requests.get(f"https://beaconcha.in/api/v1/epoch/{epoch}", headers={"accept":"application/json"})
        req.raise_for_status()
        return req.json()["data"]
    except requests.exceptions.HTTPError as err:
        logging.error(err)
        return {}

## Get scenarios
def get_scenario(scenario):
    result_list_sl = []
    for x in range(len(lidoavgbalance)):
        result_list_sl.append(get_exam_slashing(
                scenario[x][2], 
                lidoavgbalance[x]*EFFECTIVE_BALANCE_INCREMENT, 
                lidoavgeffbalance[x]*EFFECTIVE_BALANCE_INCREMENT, 
                validatorscount[x], 
                eligibleether[x]*EFFECTIVE_BALANCE_INCREMENT/validatorscount[x],
                spec = 'Bellatrix'
                )['total_loss'])
    
    result_list = []
    for x in range(len(lidoavgbalance)):
        if scenario[x][0] ==0: result_list.extend([0])
        else:
            result_list.append(get_exam_offline(
                scenario[x][1]*24*3600/SECONDS_PER_SLOT/SLOTS_PER_EPOCH, 
                scenario[x][0], 
                lidoavgbalance[x]*EFFECTIVE_BALANCE_INCREMENT, 
                lidoavgeffbalance[x]*EFFECTIVE_BALANCE_INCREMENT, 
                validatorscount[x], 
                eligibleether[x]*EFFECTIVE_BALANCE_INCREMENT/validatorscount[x], 
                spec = 'Bellatrix'
                )['total_loss'])
    df_result = pd.DataFrame({'loss_slashings':result_list_sl, 'loss_offline': result_list}, index = ['scenario_1', 'scenario_2', 'scenario_3'])
    df_result['total_loss'] = df_result.loss_slashings + df_result.loss_offline
    df_result['lidostakeddeposits'] = [lidostakeddeposits[0], lidostakeddeposits[1], lidostakeddeposits[2]]
    df_result['lido_insurance_fund'] = [lido_insurance_fund[0], lido_insurance_fund[1], lido_insurance_fund[2]]
    df_result['%_of_lido_deposits'] = df_result.total_loss/df_result.lidostakeddeposits*100
    df_result['%_of_lido_funds'] = df_result.total_loss/df_result.lido_insurance_fund*100
    pd.options.display.float_format = '{:,.2f}'.format
    print(df_result[['total_loss','loss_slashings', 'loss_offline', '%_of_lido_deposits','%_of_lido_funds']])

def get_scenarios(scenarios):
    for scenario in scenarios:
        print('\n', scenario, ": ", scenarios[scenario][-1])
        print("\nParams")
        index = ['validators offline', 'days offline', 'validators slashed']
        pd.options.display.float_format = '{:,.0f}'.format
        print(pd.concat([pd.DataFrame({'scenario_1':scenarios[scenario][0]},index = index).T,pd.DataFrame({'scenario_2':scenarios[scenario][1]},index = index).T, pd.DataFrame({'scenario_3':scenarios[scenario][2]},index = index).T]))
        scenario_exam = scenarios[scenario]
        print("\nResults")
        get_scenario(scenario_exam)
        print()

## Get aggregated results
# def get_results_offline(exams, epochs_offline):
    
#     specs = ['Bellatrix']
#     results = [get_result_offline(epochs_offline, exams, state, spec) for spec in specs for state in states]
#     titles = [(state, spec) for spec in specs for state in states]
#     for result in range(len(results)):
#         pd.options.display.float_format = '{:,.2f}'.format
#         print(titles[result], str(epochs_offline)+' epochs_offline')
#         print(results[result])
#         print()
#     #return results

def get_results_slashing(exams):
    specs = ['Bellatrix']
    results = [get_result_slashing(exams, state, spec, slashed_validators_porcentage_a, slashed_validators_porcentage_b, slashed_validators_porcentage_c, slashed_validators_porcentage_d) for spec in specs for state in states]
    titles = [(state, spec) for spec in specs for state in states]
    for result in range(len(results)):
        pd.options.display.float_format = '{:,.2f}'.format
        print(titles[result])
        print(results[result])
        print()
    #return results

## Get result for a given state (current, future) and spec (Altair, Bellatrix)

# def get_result_offline(epochs_offline, exams, state, spec):

#     if state == 'future': x = 1
#     else: x = 0

#     result_list = [get_exam_offline(
#         epochs_offline, 
#         exams[y][x], 
#         lidoavgbalance[x]*EFFECTIVE_BALANCE_INCREMENT, 
#         lidoavgeffbalance[x]*EFFECTIVE_BALANCE_INCREMENT, 
#         validatorscount[x], 
#         eligibleether[x]*EFFECTIVE_BALANCE_INCREMENT/validatorscount[x],  
#         spec
#         ) for y in range(len(exams))]

#     df_result = pd.DataFrame(
#         result_list, 
#         index = [
#             'single big operator, 30% validators offline',
#             'single big operator, 100% validators offline',
#             'two big operators, 30% validators offline',
#             'two big operators, 100% validators offline'])
#     df_result['%_of_lido_deposits'] = df_result.total_loss/lidostakeddeposits[x]*100
#     df_result['%_of_5y_earnings'] = df_result.total_loss/lido_insurance_fund[x]*100
#     return df_result[['total_loss','%_of_lido_deposits','%_of_5y_earnings']]

def get_result_slashing(exams, state, spec, slashed_validators_porcentage_a, slashed_validators_porcentage_b, slashed_validators_porcentage_c, slashed_validators_porcentage_d):

    if state == 'scenario_2': x = 1
    elif state == 'scenario_3': x = 2
    else: x = 0

    result_list = [get_exam_slashing(
        exams[y][x], 
        lidoavgbalance[x]*EFFECTIVE_BALANCE_INCREMENT, 
        lidoavgeffbalance[x]*EFFECTIVE_BALANCE_INCREMENT, 
        validatorscount[x], 
        eligibleether[x]*EFFECTIVE_BALANCE_INCREMENT/validatorscount[x], 
        spec
        ) for y in range(len(exams))]

    df_result = pd.DataFrame(
        result_list, 
        index = [
            "{:,.0%}".format(slashed_validators_porcentage_a) + ' total validators slashed',
            "{:,.0%}".format(slashed_validators_porcentage_b) + ' total validators slashed',
            "{:,.0%}".format(slashed_validators_porcentage_c) + ' total validators slashed',
            "{:,.0%}".format(slashed_validators_porcentage_d) + ' total validators slashed'])
    df_result['%_of_lido_deposits'] = df_result.total_loss/lidostakeddeposits[x]*100
    df_result['%_of_lido_funds'] = df_result.total_loss/lido_insurance_fund[x]*100
    return df_result[['total_loss','%_of_lido_deposits','%_of_lido_funds']]

## Get result for a given exam

def get_exam_offline(epochs_offline, exam, lidoavgbalance, lidoavgeffbalance, validatorscount, avarage_effective_balance, spec):
    dic = {}
    result = functions.process_offline_validator_bellatrix(epochs_offline, lidoavgbalance, lidoavgeffbalance, validatorscount, avarage_effective_balance) 
    prob_number_validators_assigned = functions.get_probability_outcomes(exam, validatorscount, 0.99, SYNC_COMMITTEE_SIZE)*result[4]
    dic.update({'offline_count': exam})
    dic.update({'total_loss_offline_penalty': functions.gwei_to_ether((result[0]-lidoavgbalance)*exam)})
    dic.update({'average_loss_offline_penalty': functions.gwei_to_ether(result[0]-lidoavgbalance)})
    dic.update({'total_loss': functions.gwei_to_ether((result[0]-lidoavgbalance)*(exam-prob_number_validators_assigned)+(result[2]-lidoavgbalance)*prob_number_validators_assigned)})
    dic.update({'average_loss': functions.gwei_to_ether(result[2]-lidoavgbalance)})
    return dic

def get_exam_slashing(exam, lidoavgbalance, lidoavgeffbalance, validatorscount, avarage_effective_balance, spec):
    dic = {}
    result = functions.process_slashings_bellatrix(exam, lidoavgbalance, lidoavgeffbalance, validatorscount, avarage_effective_balance)   
    dic.update({'slashings_count': exam})
    dic.update({'total_loss': functions.gwei_to_ether((result[0]-lidoavgbalance)*exam)})
    dic.update({'average_loss': functions.gwei_to_ether(result[0]-lidoavgbalance)})
    return dic

## MAIN
# current state of beacon chain
current_epoch_data = get_epoch_data(get_epoch_data()['epoch']-1)
# print(current_epoch_data)
validatorscount_current = int(current_epoch_data['validatorscount'])
current_epoch = current_epoch_data['epoch']
totalvalidatorbalance_current = current_epoch_data['totalvalidatorbalance']
eligibleether_current=current_epoch_data['eligibleether']
average_effective_balance = eligibleether_current/validatorscount_current

# Lido param
current_lido_deposits = 8644617
scenario_1_lido_treasury = 6215
scenario_2_lido_treasury = scenario_1_lido_treasury + 35528 * 0.8
scenario_3_lido_treasury = scenario_2_lido_treasury + (4420000 + 2250000) * 0.8 / 1630

scenario_1_lido_share = current_lido_deposits/functions.gwei_to_ether(current_epoch_data['eligibleether'])
scenario_2_lido_share = scenario_1_lido_share
scenario_3_lido_share = scenario_1_lido_share

scenario_1_lido_validator_average_eff_balance = MAX_EFFECTIVE_BALANCE
scenario_2_lido_validator_average_eff_balance = scenario_1_lido_validator_average_eff_balance
scenario_3_lido_validator_average_eff_balance = scenario_1_lido_validator_average_eff_balance

scenario_1_lido_validator_average_balance = 32000000000 #32905178993.948082
scenario_2_lido_validator_average_balance = 32000000000
scenario_3_lido_validator_average_balance = 32000000000
period_offline = 256 #epochs
lido_validators = 259019

# params for calculation
validatorscount = np.array([validatorscount_current, validatorscount_current, validatorscount_current])
eligibleether = validatorscount*(functions.gwei_to_ether(average_effective_balance))
lidoshare = [scenario_1_lido_share, scenario_2_lido_share, scenario_3_lido_share]
lido_insurance_fund = [scenario_1_lido_treasury, scenario_2_lido_treasury, scenario_3_lido_treasury]
lidostakeddeposits = [eligibleether[x]*lidoshare[x] for x in range(len(lidoshare))]
lidoavgeffbalance = functions.gwei_to_ether(np.array([scenario_1_lido_validator_average_eff_balance, scenario_2_lido_validator_average_eff_balance, scenario_3_lido_validator_average_eff_balance]))
lidoavgbalance = functions.gwei_to_ether(np.array([scenario_1_lido_validator_average_balance, scenario_2_lido_validator_average_balance, scenario_3_lido_validator_average_balance]))

slashed_validators_porcentage_a = 0.05
slashed_validators_porcentage_b = 0.1
slashed_validators_porcentage_c = 0.15
slashed_validators_porcentage_d = 0.2

exams = [
    [slashed_validators_porcentage_a * lido_validators, slashed_validators_porcentage_a * lido_validators, slashed_validators_porcentage_a * lido_validators],
    [slashed_validators_porcentage_b * lido_validators, slashed_validators_porcentage_b * lido_validators, slashed_validators_porcentage_b * lido_validators],
    [slashed_validators_porcentage_c * lido_validators, slashed_validators_porcentage_c * lido_validators, slashed_validators_porcentage_c * lido_validators],
    [slashed_validators_porcentage_d * lido_validators, slashed_validators_porcentage_d * lido_validators, slashed_validators_porcentage_d * lido_validators]]

inputdata = {
        'total active validators': validatorscount,
        'total eligible ETH': eligibleether,
        "Lido's share": lidoshare,
        "Lido's deposits": lidostakeddeposits,
        "Lido's reserves": lido_insurance_fund,
        "Average effective balance of Lido's validators": lidoavgeffbalance,
        "Average balance of Lido's validators": lidoavgbalance,
        "{:,.0%}".format(slashed_validators_porcentage_a) + ' total validators slashed': exams[0],
        "{:,.0%}".format(slashed_validators_porcentage_b) + ' total validators slashed':exams[1],
        "{:,.0%}".format(slashed_validators_porcentage_c) + ' total validators slashed':exams[2],
        "{:,.0%}".format(slashed_validators_porcentage_d) + ' total validators slashed':exams[3]}
df_inputdata = pd.DataFrame(inputdata).T
df_inputdata.columns=['scenario_1', 'scenario_2', 'scenario_3']

days_offline = 7
scenarios ={
    # 'Scenario 1':[[lidobigoperator[0][0]*1.0,days_offline,0],[lidobigoperator[1][0]*1.0,days_offline,0],'Max risk offline (single big operator, 100% validators offline for 7 days)'],
    'Scenario 2':[[0,0,51803.8],[0,0,51803.8], [0,0,51803.8],'Min risk slashings (300 validators slashed)']
    # 'Scenario 3':[[lidobigoperator[0][0]*1.0,days_offline,lidobigoperator[0][0]*0.3],[lidobigoperator[1][0]*1.0,days_offline,lidobigoperator[1][0]*0.3],'Medium risk slashings (single big operator, 30% validators slashed, 100% validators offline for 7 days)'],
    # 'Scenario 4':[[0,0,lidobigoperator[0][0]*1.0],[0,0,lidobigoperator[1][0]*1.0],'Max risk slashings (single big operator, 100% validators slashed)']
    }

# OUTCOMES
#input data
print("\nPARAMS\n")
print(df_inputdata)

# offline penalties modeling
# print("\n\nOFFLINE PENALTIES MODELING\n")
# get_results_offline(exams, period_offline)

# slashing penalties modeling
print("\n\nSLASHING PENALTIES MODELING\n")
get_results_slashing(exams)

# # # scenarios modelling
# print("\n\nSCENARIOS MODELING\n")
# get_scenarios(scenarios)