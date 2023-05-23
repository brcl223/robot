clc;
clearvars all;

d1_inch = 6;
d2_inch = 6;
d1 = in2mm(d1_inch) / 1000; % m
d2 = in2mm(d2_inch) / 1000; % m
[tau, fcm1, fcm2] = compute_torque_and_forces(d1,d2);

fprintf("d1[in]: %6.2f, d2[in]: %6.2f\ntau[Nm]: %6.4f, fcm1[N]: %6.4f, fcm2[N]: %6.4f\n", ...
    d1_inch, d2_inch, tau, fcm1, fcm2);


function [inch] = mm2in(mm)
    inch = mm / 25.4;
end


function [mm] = in2mm(inch)
    mm = inch * 25.4;
end


function [tau, fcm1, fcm2] = compute_torque_and_forces(d1, d2)
    W = 0.00635; % m
    H = 0.0381; % m
    g = 9.81; % m/s^2
    rho = 1300; % kg/m^3 (plastic)
    F2 = 2.45; % N (motor assembly at joint 2)

    fcm1 = (W*H*d1) * rho * g;
    fcm2 = (W*H*d2) * rho * g;
    tau = 0.5 * d1 * fcm1 + d1 * F2 + (d1 + 0.5 * d2) * fcm2;
end