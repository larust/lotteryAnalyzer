clear all
close all
clc

%p=nchoosek(5,5:0).*nchoosek(35,0:5)./nchoosek(40
p=NaN(1,6);
for i=0:5
    p(i+1)=nchoosek(5,5-i)*nchoosek(35,0+i)/nchoosek(40,5);
end

y = hygepdf(0:5,40,5,5)

(5-4)/(40-5)*hygepdf(4,40,5,5)