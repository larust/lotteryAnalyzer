function [rprof]=lotteryProfit(lastWin,addWin)
tPrice=130;
rPay=0.45;
rFP=0.57;
Nsplit=0:20;

pWin=1/nchoosek(40,5);

N=addWin/(rPay*rFP*tPrice);

[x, lambda]=meshgrid(Nsplit,N*pWin);
p=poisspdf(x,lambda);

costAll=nchoosek(40,5)*tPrice;

[lastWinMat,addWinMat]=meshgrid(lastWin,addWin);
myWin=lastWinMat+addWinMat+costAll*rPay*rFP;
myWin=repmat(myWin,[1, 1, length(Nsplit)]);
p=repmat(permute(p,[1 3 2]),[1 length(lastWin) 1]);
x=repmat(permute(x,[1 3 2]),[1 length(lastWin) 1]);

smallerWin=(1-rFP)*rPay*costAll;
weightedWin=sum(p./(x+1).*myWin,3);

totWin=weightedWin+smallerWin;
profit=totWin-costAll;
rprof=profit/costAll;