clear all
close all
clc

lastWin=0;
tPrice=130;
rPay=0.45;
rFP=0.57;
Nsplit=0:20;

pWin=1/nchoosek(40,5);

addWin=linspace(0,7e7,200);
N=addWin/(rPay*rFP*tPrice);
[~, lambda]=meshgrid(Nsplit,N*pWin);
[Nwin, Nrows]=meshgrid(Nsplit,N);
p=poisspdf(Nwin,lambda);
pBinom = binopdf(Nwin,floor(Nrows),pWin);
pMore=1-sum(p(:,1:6),2);
pBinomMore=1-sum(pBinom(:,1:6),2);

currentWin=(N*tPrice*rPay*rFP+lastWin);


currentWin=currentWin*1e-6;
figure('Position',[100 100 550 300]);
plot(currentWin,p(:,1:6)*100,currentWin,pMore*100)
legend('0','1','2','3','4','5','5<')
xlim([0 70])
xlabel('Upphæð sem bætist við pottinn [m. kr.]','FontSize',16)
ylabel('Líkur á skiptingu á fyrsta vinningi [%]','FontSize',16)
set(gca,'FontSize',16)
set(gcf,'PaperPositionMode','auto');

%figure
%plot(currentWin,pBinom(:,1:6),currentWin,pBinomMore)
%legend('0','1','2','3','4','5','5<')
%ylim([0 1])
%figure
%plot(currentWin,p(:,1:6)-pBinom(:,1:6))