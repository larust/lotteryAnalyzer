#!/usr/bin/python2
# -*- coding: utf-8 -*-
import numpy as np
from scipy.stats import poisson
from scipy.misc import comb
from scipy.optimize import brentq
import matplotlib.pyplot as plt

def lotteryROI(lastWin, curWin):
    addWin=curWin-lastWin
    #Icelandic lottery param
    #Price of each ticket
    tPrice=130
    #Payout of the lottery
    rPay=0.45
    #Percentage of payout contibuting to the jackpot
    rFP=0.57 
    numbers=40
    balls=5
    NsplitMax=21

    #Make sure input is 1d numpy arrays
    lastWin=np.atleast_1d(lastWin)
    addWin=np.atleast_1d(addWin)
    
    #Probability of winning
    Ncomb=comb(numbers,balls)
    pWin=1./Ncomb

    #Cost of buying all tickets
    N=addWin/(rPay*rFP*tPrice)
    costAll=Ncomb*tPrice

    #Probability of splitting the jackpot
    Nsplit=np.arange(0,NsplitMax)
    [x, lamb]= np.meshgrid(Nsplit, N*pWin)
    p=np.atleast_3d(poisson.pmf(x, lamb))
    x=np.atleast_3d(x)
    p=np.tile(np.transpose(p,(0,2,1)),(1, len(lastWin),1))
    x=np.tile(np.transpose(x,(0,2,1)),(1, len(lastWin),1))

    #Calculate the return on investment (ROI)
    [lastWinMat, addWinMat]=np.meshgrid(lastWin, addWin)
    lastWinMat=np.atleast_3d(lastWinMat)
    addWinMat=np.atleast_3d(addWinMat)
    myWin=lastWinMat+addWinMat+costAll*rPay*rFP
    myWinMat=np.tile(myWin,(1,1,NsplitMax))
    smallerWin=(1.-rFP)*rPay*costAll
    weightedWin=np.sum(p/(Nsplit+1.)*myWin,axis=2)
    totWin=weightedWin+smallerWin
    profit=totWin-costAll
    rprof=profit/costAll
    return rprof

def breakEven(lastWin, curWin0, curWin1):

    #Find ROI as a function of amount added to the jackpot
    f = lambda x: lotteryROI(lastWin, x)[0][0]

    #Find root
    curWinBE = brentq(f, curWin0, curWin1)
    return curWinBE

def plotROIFig(lastWin, addWin):
    rMat=lotteryROI(lastWin, lastWin+addWin)
    rMat=rMat*100
    levels=np.arange(np.around(np.min(rMat),-1),np.around(np.max(rMat),-1),10)
    CS=plt.contour(lastWin,addWin,rMat,levels)
    plt.clabel(CS, inline=2, fontsize=16, colors='k', fmt='%2.0f')
    plt.xlabel('Size of previous jackpot')
    plt.ylabel('Size of current jackpot')
    plt.title('Weighted return on investment')
    plt.savefig('roi.svg')

