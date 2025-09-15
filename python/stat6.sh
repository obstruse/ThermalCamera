#!

FILE=$1

export NO_AT_BRIDGE=1

#(32°F − 32) × 5/9 = 0°C

gnuplot  <<EOF

set datafile separator " "
set grid
set autoscale noextend
set xlabel 'seconds'
set format x '%g'

data1 = "`head -1 $FILE`"
set title data1

cut(x)=((x>75 & x<100)?x:NaN)
F2C(x) = x*5.0/9.0
C2F(x) = x*9.0/5.0

set yrange [20:100]
stats "$FILE" using 3 skip 1 nooutput
#stats "$FILE" using ((\$3+\$4+\$5)/3.0) skip 1

#set yrange [STATS_mean - 2.0 : STATS_mean + 2.0]
set yrange [ -2.0 : 2.0]
#set y2range [ F2C(-2) : F2C(2) ]
set ytics nomirror
#set ytics add ("mean" 0)
set y2tics 0.25
#set y2tics add ("mean" 0)
set ylabel 'Degrees F'
set y2label 'Degrees C'

set link y2 via F2C(y) inverse C2F(y)

RR = sprintf("RMS: %0.3f F / %0.3f C",STATS_stddev,F2C(STATS_stddev))
set style textbox 1 opaque border fc "white" margins 10,1
set label RR at graph 0.5,first 0 center boxed bs 1 front

plot STATS_stddev notitle with filledcurves y2=( -(STATS_stddev)) fs transparent solid 0.2, \
    "$FILE" using 1:(cut(\$3)-STATS_mean) title "$FILE" lt rgb "blue" lw 6 with dots, \
    (STATS_stddev) notitle  lt rgb "black", \
    0              title "Mean" dt 5 lt rgb "black", \
    -(STATS_stddev) notitle  lt rgb "black"


pause mouse button2 "button2 to exit"

EOF


