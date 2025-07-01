using CP;

int n = 20;
range I = 1..n;

// Tạo interval variable optional
dvar interval intervals[I] optional size 1;

// Ràng buộc: trong 5 biến liên tiếp, ít nhất 2 biến được chọn



// Giải mô hình
execute {
  cp.param.Workers = 8;
}

// In kết quả
execute {
  for(var i in I)
    writeln("interval[", i, "] = ", intervals[i]);
}


