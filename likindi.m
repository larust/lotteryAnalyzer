clear all
close all
clc

lastWin=94291820;
ticketPrice=130;
rPayout=0.45;
rFirstPrice=0.57;
Nsplit=0:20;

pWin=1/nchoosek(40,5);
N=linspace(0,1.5e6,500);

[x, lambda]=meshgrid(Nsplit,N*pWin);

p=poisspdf(x,lambda);
pMore=1-sum(p(:,1:5),2);

currentWin=(N*ticketPrice*rPayout*rFirstPrice+lastWin);

costAll=nchoosek(40,5)*ticketPrice;

addedWin=currentWin+costAll*rPayout*rFirstPrice;
smallerWin=(1-rFirstPrice)*rPayout*costAll;
weightedWin=sum(p./(x+1).*repmat(addedWin',1,size(x,2)),2);
totWin=weightedWin+smallerWin;
profit=totWin-costAll;
rprof=profit/costAll;

currentWin=currentWin*1e-6;
plot(currentWin,p(:,1),currentWin,p(:,2),currentWin,p(:,3),currentWin,p(:,4),currentWin,p(:,5),currentWin,pMore)
legend('0','1','2','3','4','4<')
%xlim([lastWin*1e-6 100])

figure
plot(currentWin, profit)