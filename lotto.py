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


def lotteryProfitMat(lastWin, addWin):
    #Icelandic lottery param
    tPrice=130
    rPay=0.45
    rFP=0.57
    numbers=40
    balls=5
    NsplitMax=21
    
    [lastWinMat, addWinMat]=np.meshgrid(lastWin, addWin)
    
    #Probability of winning
    Ncomb=comb(numbers,balls)
    pWin=1./Ncomb

    #Cost of buying all rows
    N=addWin/(rPay*rFP*tPrice)
    costAll=Ncomb*tPrice

    #Probability of splitting the jackpot
    Nsplit=np.arange(0,NsplitMax)
    [x, lamb]= np.meshgrid(Nsplit, N*pWin)
    p=np.atleast_3d(poisson.pmf(x, lamb))
    x=np.atleast_3d(x)
    p=np.tile(np.transpose(p,(0,2,1)),(1, len(lastWin),1))
    x=np.tile(np.transpose(x,(0,2,1)),(1, len(lastWin),1))

    lastWinMat=np.atleast_3d(lastWinMat)
    addWinMat=np.atleast_3d(addWinMat)

    #ROI of buying all possible rows
    myWin=lastWinMat+addWinMat+costAll*rPay*rFP
    myWinMat=np.tile(myWin,(1,1,NsplitMax))
    #myWin=lastWin+addWin+costAll*rPay*rFP
    smallerWin=(1.-rFP)*rPay*costAll
    weightedWin=np.sum(p/(Nsplit+1.)*myWin,axis=2)
    totWin=weightedWin+smallerWin
    profit=totWin-costAll
    rprof=profit/costAll
    return rprof


