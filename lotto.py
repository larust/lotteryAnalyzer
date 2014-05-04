import numpy as np
from scipy.stats import poisson
from scipy.misc import comb
import matplotlib.pyplot as plt

def lotteryProfit(lastWin, addWin):
    #Icelandic lottery param
    tPrice=130
    rPay=0.45
    rFP=0.57
    numbers=40
    balls=5
    NsplitMax=21

#   [lastWinMat, addWinMat]=np.meshgrid(lastWin, addWin)

    #Number of possible winners
    Nsplit=np.arange(0,NsplitMax)
    
    #Probability of winning
    Ncomb=comb(numbers,balls)
    pWin=1./Ncomb

    #Number of rows bought
    N=addWin/(rPay*rFP*tPrice)

    #Probability of splitting the jackpot
    p=poisson.pmf(Nsplit, pWin*N)

    #ROI of buying all possible rows
    costAll=Ncomb*tPrice
    myWin=lastWin+addWin+costAll*rPay*rFP
    smallerWin=(1.-rFP)*rPay*costAll
    weightedWin=np.sum(p/(Nsplit+1.)*myWin)
    totWin=weightedWin+smallerWin
    profit=totWin-costAll
    rprof=profit/costAll
    return rprof


