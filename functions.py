import numpy as np
import requests
import logging
import math
import pandas as pd
pd.options.display.float_format = '{:,.2f}'.format

SLOTS_PER_EPOCH = 32
SECONDS_PER_SLOT = 12
MIN_SLASHING_PENALTY_QUOTIENT_BELLATRIX = 2**5 # (= 32)
EPOCHS_PER_SYNC_COMMITTEE_PERIOD=2**8 # (= 256)	epochs	~27 hours
EPOCHS_PER_SLASHING = 2**13 # ~36 days or 8192 epochs
EFFECTIVE_BALANCE_INCREMENT = 2**0 * 10**9
TIMELY_SOURCE_WEIGHT=14
TIMELY_TARGET_WEIGHT=26
TIMELY_HEAD_WEIGHT=14
WEIGHT_DENOMINATOR=64
BASE_REWARD_FACTOR = 2**6
SYNC_REWARD_WEIGHT=2
SYNC_COMMITTEE_SIZE=2**9 # (= 512)	Validators	
PROPORTIONAL_SLASHING_MULTIPLIER_BELLATRIX	= 3
HYSTERESIS_QUOTIENT = 4
HYSTERESIS_DOWNWARD_MULTIPLIER = 1
HYSTERESIS_UPWARD_MULTIPLIER = 5
HYSTERESIS_INCREMENT = EFFECTIVE_BALANCE_INCREMENT // HYSTERESIS_QUOTIENT
DOWNWARD_THRESHOLD = HYSTERESIS_INCREMENT * HYSTERESIS_DOWNWARD_MULTIPLIER
UPWARD_THRESHOLD = HYSTERESIS_INCREMENT * HYSTERESIS_UPWARD_MULTIPLIER
MAX_EFFECTIVE_BALANCE = 2**5 * 10**9

## Helpers

def gwei_to_ether(amount):
    return amount/10**9

def integer_squareroot(n):
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x

def c(n, k):   # helper for large numbers binomial coefficient calculation
    if 0 <= k <= n:
        nn = 1
        kk = 1
        for t in range(1, min(k, n - k) + 1):
            nn *= n
            kk *= t
            n -= 1
        return nn // kk
    else:
        return 0

def get_probability_outcomes(exam, validatorscount, confidence, SYNC_COMMITTEE_SIZE):
    outcome = []
    for offline_validator_sync_cnt in range(0, SYNC_COMMITTEE_SIZE+1):
        outcome.append(c(int(exam), offline_validator_sync_cnt)*c(int(validatorscount-exam),SYNC_COMMITTEE_SIZE-offline_validator_sync_cnt)/c(int(validatorscount),SYNC_COMMITTEE_SIZE))
    df_outcome = pd.DataFrame(pd.Series(outcome), columns=['outcome'])
    df_outcome['cumul'] = df_outcome.outcome.cumsum()
    return df_outcome[df_outcome.cumul <= confidence].tail(1).index[0]

def process_offline_validator_bellatrix(epochs_offline, lidoavgbalance, lidoavgeffbalance, validatorscount, avarage_effective_balance):
    sync_comittees = math.ceil(epochs_offline/EPOCHS_PER_SYNC_COMMITTEE_PERIOD)
    sync_penalty_period = sync_comittees*EPOCHS_PER_SYNC_COMMITTEE_PERIOD
    balance = lidoavgbalance
    balance_sync = lidoavgbalance
    effective_balance = lidoavgeffbalance
    effective_balance_sync = lidoavgeffbalance
    total_active_balances = (validatorscount)* avarage_effective_balance
    epoch = 0
    while epoch<= epochs_offline:
        balance, effective_balance = process_offline_penalty_bellatrix(balance, effective_balance, total_active_balances)
        balance_sync, effective_balance_sync = process_offline_penalty_bellatrix(balance_sync, effective_balance_sync, total_active_balances)
        balance_sync, effective_balance_sync = process_sync_penalty_bellatrix(balance_sync, effective_balance_sync, total_active_balances)
        epoch += 1
    if epochs_offline < sync_penalty_period:
        while epoch<=sync_penalty_period:
            balance_sync, effective_balance_sync = process_sync_penalty_bellatrix(balance_sync, effective_balance_sync, total_active_balances)
            epoch += 1
    
    return balance, effective_balance, balance_sync, effective_balance_sync, sync_comittees

## Slashing penalties calculation Bellatrix

def process_slashings_bellatrix(slashed_validator_cnt, lidoavgbalance, lidoavgeffbalance, validatorscount, avarage_effective_balance):
    balance = lidoavgbalance
    effective_balance = lidoavgeffbalance
    total_active_balances = (validatorscount - slashed_validator_cnt)* avarage_effective_balance
    slashed_validator_balance = effective_balance * slashed_validator_cnt

    #initial_penalty
    balance, effective_balance = process_initial_penalty_bellatrix(balance, effective_balance)
    
    #exiting_penalty
    exiting_epoch = 0
    while exiting_epoch <= EPOCHS_PER_SLASHING//2:
        balance, effective_balance = process_offline_penalty_bellatrix(balance, effective_balance, total_active_balances)
        exiting_epoch += 1
    
    # special_penalty
    balance, effective_balance = process_special_penalty_bellatrix(balance, effective_balance, total_active_balances, slashed_validator_balance)

    #exiting_penalty
    while exiting_epoch <= EPOCHS_PER_SLASHING:
        balance, effective_balance = process_offline_penalty_bellatrix(balance, effective_balance, total_active_balances)
        exiting_epoch += 1

    return balance, effective_balance

## Penalties Bellatrix

def process_initial_penalty_bellatrix(balance, effective_balance):
    initial_penalty = effective_balance // MIN_SLASHING_PENALTY_QUOTIENT_BELLATRIX
    balance -= initial_penalty
    effective_balance = process_final_updates(balance, effective_balance)
    return balance, effective_balance

def process_offline_penalty_bellatrix(balance, effective_balance, total_active_balances):
    base_reward = effective_balance // EFFECTIVE_BALANCE_INCREMENT * (EFFECTIVE_BALANCE_INCREMENT*BASE_REWARD_FACTOR // integer_squareroot(total_active_balances)) 
    offline_penalty = (TIMELY_SOURCE_WEIGHT+TIMELY_TARGET_WEIGHT+TIMELY_HEAD_WEIGHT)/WEIGHT_DENOMINATOR * base_reward
    balance -= offline_penalty
    effective_balance = process_final_updates(balance, effective_balance)
    return balance, effective_balance

def process_special_penalty_bellatrix(balance, effective_balance, total_active_balances, slashed_validator_balance):
    special_penalty = effective_balance * min(
                    slashed_validator_balance*PROPORTIONAL_SLASHING_MULTIPLIER_BELLATRIX, total_active_balances) // total_active_balances 
    balance -= special_penalty
    effective_balance = process_final_updates(balance, effective_balance)
    return balance, effective_balance

def process_sync_penalty_bellatrix(balance, effective_balance, total_active_balances):
    total_active_increments = total_active_balances // EFFECTIVE_BALANCE_INCREMENT
    total_base_rewards = EFFECTIVE_BALANCE_INCREMENT*BASE_REWARD_FACTOR // integer_squareroot(total_active_balances) * total_active_increments
    max_participant_rewards = total_base_rewards * SYNC_REWARD_WEIGHT // WEIGHT_DENOMINATOR // SLOTS_PER_EPOCH
    participant_reward = max_participant_rewards // SYNC_COMMITTEE_SIZE
    balance -= participant_reward
    effective_balance = process_final_updates(balance, effective_balance)
    return balance, effective_balance

## Final updates

def process_final_updates(balance, effective_balance):
        # Update effective balances with hysteresis
        if (balance + DOWNWARD_THRESHOLD < effective_balance or effective_balance + UPWARD_THRESHOLD < balance):
            effective_balance = min(balance - balance % EFFECTIVE_BALANCE_INCREMENT, MAX_EFFECTIVE_BALANCE)
        return effective_balance