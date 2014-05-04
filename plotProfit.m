%function [rprof]=lotteryProfit(lastWin,currWin)
clear all
close all

load('lotto5-40-130')
xHist=[winHist(1:end-1) max(diff(winHist),0)];

nHist=size(xHist,1);

bvec=xHist(:,2)==0;
xHist(bvec,:)=[];
%xHist(bVec(2:nHist),2)=xHist(bVec(1:nHist-1),1);
%xHist(bVec(1:nHist-1),1)=0;

lastWin=linspace(0,1e8,500);
addWin=linspace(0,5e7,500);

tPrice=130;
rPay=0.45;
rFP=0.57;
Nsplit=0:20;

pWin=1/nchoosek(40,5);

N=addWin/(rPay*rFP*tPrice);

[x, lambda]=meshgrid(Nsplit,N*pWin);
p=poisspdf(x,lambda);

%currentWin=(N*tPrice*rPay*rFP+lastWin);
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

figure('Position',[100 100 550 400]);
plot(xHist(:,1)*1e-6,xHist(:,2)*1e-6,'rd')
hold on
[C,h] = contour(lastWin*1e-6,addWin*1e-6,rprof*100);
clabel(C,h,'FontSize',16)
text_handle = clabel(C,h);
%title('Vegin ávöxtun [%]')
xlabel('Potturinn var síðast (m.kr.) ','FontSize',16)
ylabel('Bæst hefur við pottinn (m.kr.) ','FontSize',16)
set(gca,'FontSize',16)
set(gcf,'PaperPositionMode','auto');