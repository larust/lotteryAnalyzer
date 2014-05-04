clear all
close all
clc

lastWin=94291820;
ticketPrice=130;
rPayout=0.45;
rFirstPrice=0.57;
Nsplit=0:20;

pWin=1/nchoosek(40,5);
N=1326531; %linspace(0,1.5e6,500);

[x, lambda]=meshgrid(Nsplit,N*pWin);

p=poisspdf(x,lambda);
pMore=1-sum(p(:,1:5),2);

currentWin=(N*ticketPrice*rPayout*rFirstPrice+lastWin);

costAll=nchoosek(40,5)*ticketPrice;

addedWin=currentWin+costAll*rPayout*rFirstPrice;
smallerWin=(1-rFirstPrice)*rPayout*rFirstPrice*costAll;
weightedWin=sum(p./(x+1).*repmat(addedWin',1,size(x,2)),2);
totWin=weightedWin+smallerWin;
profit=totWin-costAll;
rprof=profit/costAll;

figure
plot(currentWin, profit)