# 算法竞赛模板 --- hzvictory出品

# 目录

**一、STL容器**
1.1 vector
1.2 stack
1.3 string
1.4 queue/priority_queue
1.5 deque
1.6 map/multimap
1.7 set/multiset
1.8 unordered_map/unordered_set
1.9 STL算法
1.10 bitset (容器)

**二、常见小算法**
2.1 二分✅️
2.1.1 二分查找
2.1.2 二分答案模板
2.1.3 二分答案使用说明
2.1.4 浮点数二分（实数二分）
2.1.5 二分查找函数：lower_bound 和 upper_bound
2.1.6 二分总结

2.2 数论-数学题✅️
2.3 数据结构类✅️
2.3.1 并查集
2.3.2 树状数组
2.3.3 线段树

2.4 图论类✅️
2.4.1 拓扑排序
2.4.2 最短路
2.4.3 生成树
2.4.4 最近公共祖先(LCA)
2.4.5 树链剖分

2.5 动态规划类✅️
2.5.1 最长公共子序列
2.5.2 树形dp

2.6 字符串类✅️
2.6.1 字符串哈希
2.6.2 字典树
2.6.3 KMP
2.6.4 manacher

2.7 杂项 ✅️
2.7.1 快速幂，逆元，排列组合C&&A, gcd , lcm , 判断素数,进制转换
2.7.2 python日期处理函数
2.7.3 函数杂项

**三 、经验环节**
3.1 算法竞赛中时间复杂度、数据范围与时间限制 的关系
3.2 由数据范围反推算法复杂度以及算法内容





# 一、STL容器

## 1.1 vector

**定义方式：**

![page image](E:/桌面/acm相关/模板/模板_assets/page_010_011.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_011_012.png)

## 1.2 stack

![page image](E:/桌面/acm相关/模板/模板_assets/page_011_013.png)

## 1.3 string

![page image](E:/桌面/acm相关/模板/模板_assets/page_012_014.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_013_015.png)

## 1.4 queue/priority_queue

![page image](E:/桌面/acm相关/模板/模板_assets/page_014_016.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_014_017.png)

## 1.5 deque

![page image](E:/桌面/acm相关/模板/模板_assets/page_014_018.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_015_019.png)

## 1.6 map/multimap

![page image](E:/桌面/acm相关/模板/模板_assets/page_015_020.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_016_021.png)

## 1.7 set/multiset

![page image](E:/桌面/acm相关/模板/模板_assets/page_016_022.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_017_023.png)

## 1.8 unordered_map/unordered_set

![page image](E:/桌面/acm相关/模板/模板_assets/page_017_024.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_018_025.png)

## 1.9 STL算法

![page image](E:/桌面/acm相关/模板/模板_assets/page_019_026.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_020_027.png)

## 1.10 bitset (容器)

使用 bitset 类型需

```cpp
 #include <bitset>
```

定义方式

![page image](E:/桌面/acm相关/模板/模板_assets/page_020_028.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_021_029.png)

# 二、常见小算法

## 2.1 二分✅️

### 2.1.1二分查找

#### while(l<r)

**尽量向左找目标**

```c++
//在a数组中寻找第一个>=x的数，并返回其下标
int bsearch_1(int l, int r)
{
    while (l < r)
    {
        int mid = l + r >> 1;//或写成(l+r)/2
        if (a[mid]>=x) r = mid;
        else l = mid + 1;
    }
    return l;//因为while循环当l==r时终止，return r也可以
}

```

**尽量向右找目标**

```c++
//在a数组中寻找最后一个<=x的数，并返回其下标
int bsearch_2(int l, int r)
{
    while (l < r)
    {
        int mid = l + r + 1 >> 1;//或写成(l+r+1)/2
        if (a[mid]<=x) l = mid;
        else r = mid - 1;
    }
    return l;//因为while循环当l==r时终止，return r也可以
}

```



#### while(l<=r)

**尽量向左找目标**

```c++
//在a数组中寻找第一个>=x的数，并返回其下标
int bsearch_1(int l, int r)
{
	int res=0x3f3f3f3f//可以先将res设置为一个很大的数，如果while循环终止后res没变，便没找到
    while (l <= r)
    {
        int mid = l + r >> 1;//或写成(l+r)/2
        if (a[mid]>=x){
        	r = mid-1;
        	res=mid;
        } 
        else l = mid + 1;
    }
    return res;
}

```

**尽量向右找目标**

```c++
//在a数组中寻找最后一个<=x的数，并返回其下标
int bsearch_2(int l, int r)
{
	int res=0x3f3f3f3f//可以先将res设置为一个很大的数，如果while循环终止后res没变，便没找到
    while (l <= r)
    {
        int mid = l + r >> 1;//或写成(l+r)/2
        if (a[mid]<=x){
        	l = mid+1;
        	res=mid;
        } 
        else r = mid - 1;
    }
    return res;
}

```







### 2.1.2 二分答案模板

**尽量向左找答案**

```c++
//求最小的最大值
int bsearch_1(int l, int r)
{
    while (l < r)
    {
        int mid = l + r >> 1;
        if (check(mid)) r = mid;
        else l = mid + 1;
    }
    return l;
}

```

**尽量向右找目标答案**

```c++
//求最大的最小值
int bsearch_2(int l, int r)
{
    while (l < r)
    {
        int mid = l + r + 1 >> 1;
        if (check(mid)) l = mid;
        else r = mid - 1;
    }
    return l;
}



```



### 2.1.3 二分答案使用说明 

**什么时候该使用二分答案？**

1、答案在一个区间内（一般情况下，区间会很大，暴力超时）
2、直接搜索不好搜，但是容易判断一个答案可行不可行
3、该区间对题目具有单调性，即：在区间中的值越大或越小，题目中的某个量对应增加或减少。
4、关键词：求…最大值的最小值 、 求…最小值的最大值、求满足条件下的最小（大）值、 求最靠近一个值的值、 求最小的能满足条件的代价…



**怎样二分答案？**

**1.找具有单调性的答案区间（l= …,r=…）**

如何理解答案的单调性呢？可以见下图，该图表示一个区间，从左到右要实现的代价逐渐增高，我们要在这个区间里找到一个代价最小的满足条件的答案。观察图可以发现，位于答案左边的区间不满足条件，位于答案右边的区间满足条件，像这种要么一边不满足，要么一边都满足的现象就是答案的单调性。


答案的单调性大多数情况下可以转化为一个函数，其单调性证明多种多样，如下：

移动石头的个数越多，答案越大（NOIP2015跳石头）。
前i天的条件一定比前 i + 1 天条件更容易（NOIP2012借教室）。
满足更少分配要求比满足更多的要求更容易（NOIP2010关押罪犯）。
满足更大最大值比满足更小最大值的要求更容易（NOIP2015运输计划）。
时间越长，越容易满足条件（NOIP2012疫情控制）。

**2.设计check函数**
这个具体题目具体分析，可以看例题感受一下，究其根本还是要多做题，无他，唯手熟尔

**3.套模板**
不用我多说了吧





### 2.1.4浮点数二分（实数二分）

思路和整数二分一样，区别是浮点型二分不需要注意边界问题（也就是不需要+1/-1）

```c++
	while(r-l>1e-5) //需要一个精度保证
	{
		double mid = (l+r)/2;
		if(check(mid)) l=mid; //或r=mid;
		else r=mid; //或l=mid;
	}

```

例题：给数n，求n的立方根

```c++
#include<bits/stdc++.h>
using namespace std;
 
const double eps=1e-7;
int main(){
  double n,m;
  cin>>n;
  while(n--){
    cin>>m;   
    double l=0,r=m;
    while(r-l>eps){
      double mid=(r+l)/2;
      if(pow(mid,3)>=m) r=mid;
      else l=mid;
    }
    printf("%0.3lf\n",l);
  }
  return 0;
}
```



### 2.1.5 二分查找函数 ：lower_bound 和 upper_bound 

这两个是C++的`STL`库封装的两个二分查找函数，使用时需要加上头文件

```c++
#include<algorithm>
```

使用方法和sort函数很像，可以用`greater< type >` 重载，也可以自定义比较函数，具体可以翻阅相关博客，在这里只简单介绍一下基本的使用方法

**upper_bound**

```c++
upper_bound(begin, end, value)
//在从小到大的排好序的数组中，在数组的 [begin, end) 区间中二分查找第一个大于value的数，找到返回该数字的地址，没找到则返回end。
    
upper_bound(begin, end, value, greater<int>())
//在从大到小的排好序的数组中，在数组的 [begin, end) 区间中二分查找第一个小于value的数，找到返回该数字的地址，没找到则返回end。
```

**lower_bound**

```
lower_bound(begin, end, value)
//在从小到大的排好序的数组中，在数组的 [begin, end) 区间中二分查找第一个大于等于value的数，找到返回该数字的地址，没找到则返回end。
    
lower_bound(begin, end, value, greater<int>())
//在从大到小的排好序的数组中，在数组的 [begin, end) 区间中二分查找第一个小于等于value的数，找到返回该数字的地址，没找到则返回end。

```

注意，返回的是地址，不是下标，也不是数值！！！

接下来举个例子，讲解一下在实际中怎么用

```c++
#include <iostream>
#include <algorithm>
using namespace std;
int main(){
    int a[] = {1, 2, 3, 3, 3, 4, 4, 5, 6};
    int x = 3;
    //查找第一个>x的元素,并输出其下标
    cout << upper_bound(a, a + 9, x) - a;   //输出 5（下标）
    // 查找第一个>x的元素,并输出其数值
    auto i = upper_bound(a, a + 9, x);
    cout << *i;                             //输出4（数值）
    
    //查找第一个>=x的元素,并输出其下标
    cout << lower_bound(a, a + 9, x) - a;   //输出 2（下标）
    // 查找第一个>=x的元素,并输出其数值
    auto j = lower_bound(a, a + 9, x);
    cout << *j;                             //输出3（数值）
}

```

该函数的前两个参数及其重载方式和`sort（）`函数差不多，如果不了解的话可以去学习一下`sort（）`的相关语法，类比一下就懂了



### 2.1.6 二分总结

**二分模板一共有两个，分别适用于不同情况。**
**算法思路：假设目标值在闭区间`[l, r]`中， 每次将区间长度缩小一半，当`l = r`时，我们就找到了目标值。**



当我们将区间`[l, r]`划分成`[l, mid]`和`[mid + 1, r]`时，其更新操作是`r = mid`或者`l = mid + 1`;，计算`mid`时不需要加1。

```c++
int bsearch_1(int l, int r)
{
    while (l < r)
    {
        int mid = l + r >> 1;
        if (check(mid)) r = mid;
        else l = mid + 1;
    }
    return l;
}

```



当我们将区间`[l, r]`划分成`[l, mid - 1]`和`[mid, r]`时，其更新操作是`r = mid - 1`或者`l = mid`;，此时为了防止死循环，计算`mid`时需要加1。

```c++
int bsearch_2(int l, int r)
{
    while (l < r)
    {
        int mid = l + r + 1 >> 1;
        if (check(mid)) l = mid;
        else r = mid - 1;
    }
    return l;
}

```



## 2.2 数论-数学题✅️

无无无无无无    --------------   你hzvictory同志不爱写数学

## 2.3 数据结构类✅️

### 2.3.1并查集

#### **并查集代码 （路径压缩）: **

```cpp
int w[N];
for (int i = 1; i <= n; i ++ ) w[i] = i;

int find(int i){
    if(w[i]==i) return i;
    else return w[i] = find(w[i]);
}
bool add(int x, int y) 
{
    x = find(x);
    y = find(y);
    if (x == y) return false;   //需要判断的时候就加
    p[y] = x;					//不需要判断的时候直接if(x!=y) p[y]=x;
    return true;
}

```

#### 带权并查集

路径压缩算法之二（加权标记法）
备注：
不要一看到“加权标记”这种比较高大上的名词就害怕，其实他也是属于路径压缩算法，不同的是其思想更加高级（更不容易想到）罢了。不过我还是说一下，掌握了前面几点内容就能应对绝大多数ACM问题，下面的“加权标记法”供有兴趣的同学学习交流。

主要思路：
加权标记法需要将树中所有节点都增设一个权值，用以表示该节点所在树中的高度（比如用rank[x]=3表示 x 节点所在树的高度为3）。这样一来，在合并操作的时候就能通过这个权值的大小来决定谁当谁的上级（玄慈哭了：“正义终会来到，但永不会缺席”）。
在合并操作的时候，假设需要合并的两个集合的代表元（教主）分别为 x 和 y，则只需要令pre[x] = y 或者pre[y] = x 即可。但我们为了使合并后的树不产生退化（即：使树中左右子树的深度差尽可能小），那么对于每一个元素 x ，增设一个rank[x]数组，用以表达子树 x 的高度。在合并时，如果rank[x] < rank[y]，则令pre[x] = y；否则令pre[y] = x。
举个例子，我们对以A，F为代表元的集合进行合并操作（如下图所示）：

![6c24d3658bf90d7e0fbc9b3493309d97](D:\i_love_qq\Tencent Files\3215763265\nt_qq\nt_data\Pic\2026-05\Ori\6c24d3658bf90d7e0fbc9b3493309d97.png)

由于rank(A) > rank(F) ，因此令pre[F]= A。合并后的图形如下图所示：

![7d1c024ce4839504bb75d9828464f7dd](D:\i_love_qq\Tencent Files\3215763265\nt_qq\nt_data\Pic\2026-05\Ori\7d1c024ce4839504bb75d9828464f7dd.png)

可以看出，合并前两个树的最大高度为3，合并后依然是3，这也就达到了我们的目的。但如果令pre[A]= F，那么就会使得合并后的树的总高度增加，这里我就不上图了，同学们不信可以自己画出来看看。
我们常说，鱼和熊掌不可兼得，同理，时间复杂度和空间复杂度也很难兼得。由于给每个节点都增加了一个权值来标记其在树中的高度，这也就意味着需要额外的数据结构来存放权重信息，所以这将导致额外的空间开销。

实现：
加权标记法的核心在于对rank数组的逻辑控制，其主要的情况有：
1、如果rank[x] < rank[y]，则令pre[x] = y；
2、如果rank[x] == rank[y]，则可任意指定上级；
3、如果rank[x] > rank[y]，则令pre[y] = x；
在实际写代码时，为了使代码尽可能简洁，我们可以将第1点单独作为一个逻辑选择，然后将2、3点作为另一个选择（反正第2点任意指定上级嘛），所以具体的代码如下：

```cpp
void union(int x,int y)
{
    x=find(x);							// 寻找 x 的代表元
    y=find(y);							// 寻找 y 的代表元
    if(x==y) return ;					// 如果 x和 y 的代表元一致，说明他们共属同一集合，则不需要合并，直接返回；否则，执行下面的逻辑
    if(rank[x]>rank[y]) pre[y]=x;		// 如果 x的高度大于 y，则令 y 的上级为 x
    else								// 否则
    {
        if(rank[x]==rank[y]) rank[y]++;	// 如果 x 的高度和 y 的高度相同，则令 y 的高度加1
        pre[x]=y;						// 让 x 的上级为 y
    }
}

```

#### 总结

1、用集合中的某个元素来代表这个集合，则该元素称为此集合的代表元；
2 、一个集合内的所有元素组织成以代表元为根的树形结构；
3 、对于每一个元素 x，pre[x] 存放 x 在树形结构中的父亲节点（如果 x 是根节点，则令 pre[x] = x）；
4 、对于查找操作，假设需要确定 x 所在的的集合，也就是确定集合的代表元。可以沿着 pre[x] 不断在树形结构中向上移动，直到到达根节点。
因此，基于这样的特性，并查集的主要用途有以下两点：
1、维护无向图的连通性（判断两个点是否在同一连通块内，或增加一条边后是否会产生环）；
2、用在求解最小生成树的Kruskal算法里。


一般来说，一个并查集对应三个操作：
1、初始化（ Init()函数 ）
2、查找函数（ Find()函数 ）
3、合并集合函数（ Join()函数 ）


下面给出上述所有内容的代码汇总：

```cpp
const int  N=1005					// 指定并查集所能包含元素的个数（由题意决定）
int pre[N];     					// 存储每个结点的前驱结点 
int rank[N];    					// 树的高度 
void init(int n)     				// 初始化函数，对录入的 n 个结点进行初始化 
{
    for(int i = 0; i < n; i++){
        pre[i] = i;     			// 每个结点的上级都是自己 
        rank[i] = 1;    			// 每个结点构成的树的高度为 1 
    } 
}
int find(int x)     	 		    // 查找结点 x 的根结点 
{
    if(pre[x] == x) return x;  		// 递归出口：x 的上级为 x 本身，则 x 为根结点 
    return find(pre[x]); 			// 递归查找 
} 
 
int find(int x)     				// 改进查找算法：完成路径压缩，将 x 的上级直接变为根结点，那么树的高度就会大大降低 
{
    if(pre[x] == x) return x;		// 递归出口：x 的上级为 x 本身，即 x 为根结点 
    return pre[x] = find(pre[x]);   // 此代码相当于先找到根结点 rootx，然后 pre[x]=rootx 
} 

bool isSame(int x, int y)      		// 判断两个结点是否连通 
{
    return find(x) == find(y);  	// 判断两个结点的根结点（即代表元）是否相同 
}

bool join(int x,int y)
{
    x = find(x);						// 寻找 x 的代表元
    y = find(y);						// 寻找 y 的代表元
    if(x == y) return false;			// 如果 x 和 y 的代表元一致，说明他们共属同一集合，则不需要合并，返回 false，表示合并失败；否则，执行下面的逻辑
    if(rank[x] > rank[y]) pre[y]=x;		// 如果 x 的高度大于 y，则令 y 的上级为 x
    else								// 否则
    {
        if(rank[x]==rank[y]) rank[y]++;	// 如果 x 的高度和 y 的高度相同，则令 y 的高度加1
        pre[x]=y;						// 让 x 的上级为 y
	}
	return true;						// 返回 true，表示合并成功
}

```



### 2.3.2 树状数组

#### 树状数组模板:

```

```

#### 小原理讲解：

#### 一，简介

树状数组（Fenwick Tree）是一种高效的数据结构，主要用于解决区间查询和单点更新问题，时间复杂度均为 O(logn)，适用于数组长度固定且需要频繁进行这两种操作的场景。是一种可以“动态求区间和”的树形数据结构，但并没有真正的构造出边来，所以是“树状的”。

以下是其核心知识点：
1. 基本原理
（1）结构特点：树状数组通过将数组元素按照二进制低位的 “1” 进行分层存储，形成一个树形结构（非传统二叉树），每个节点负责存储特定区间的前缀和。
2，核心操作：
（1）单点更新：修改某个元素的值，并更新其所有相关父节点。
（2）前缀和查询：计算从数组第一个元素到指定位置的前缀和，进而推导出区间和。

#### 二，区分与前缀和的区别和联系

1. 时间复杂度
操作    前缀和    树状数组
初始化    O(n)  O(nlogn)或 O(n)
单点修改O(n)     O(logn)
区间查询O(1)     O(logn)
区间修改O(n)(需配合差分) O(logn)
2. 空间复杂度
前缀和：
O(n) （需要额外存储前缀和数组）。
树状数组：
O(n) （直接在原数组基础上维护树状结构）。
3. 适用场景
前缀和：适合静态数组（不涉及修改），频繁查询区间和。
例如：多次查询数组中任意子数组的和。
树状数组：适合动态数组（需频繁修改和查询）。
例如：单点修改后快速查询前缀和、区间修改与查询（需配合差分）。
4. 实现灵活性
前缀和：仅支持区间和查询，难以扩展到其他操作（如区间最大值）。
树状数组：可扩展支持多种操作，如区间最大值 / 最小值（需调整更新策略）。

#### 三，基本步骤演示

1，lowbit操作
是一种位运算操作，用于计算出数字的二进制表达中的最低位的1以及后面所有的0
int lowbit(int x){return x&-x}; o(1)

```cpp
int lowbit(int x)//用于快速计算一个整数在二进制表示下最低位的 1 所对应的值
{
	return x & -x;
}
/*x = 6      → 二进制: 0000 0110
~x         → 二进制: 1111 1001
~x + 1 = -x → 二进制: 1111 1010
x & (-x)   → 二进制: 0000 0010  → 十进制: 2*/
//lowbit(x) 的值等于 2^k，其中 k 是 x 的二进制末尾连续 0 的个数
```

2，lowbit和树状数组t[]的联系
 int t[](tree),大小和我们需要维护的数组大小一样即可
 树状数组的结构：t[i]存储a[i]中一段区间和：
 定义t[i]存储以i结尾，且区间大小为lowbit(i)的区间和
 t[j]=sigma(j=(i-lowbit(i)+1)~~~i)a[j],可以将[i-lowbit(i)+1,i]称为“管辖区间”
 例子：a1 a2 a3 a4.....................an(分别为1 2 3 4 ..........n)
 t1-->1 t2-->[1,2]  t3-->3 t4-->[1,4] t5-->5 t6-->[5,6] t7-->7 t8-->[1,8]
 如何进行单点修改？举个例子：假设要修改a[3],包含a[3]的区间有t3 t4 t8,所以应该修改这3个节点
 只需进行+lowbit操作即可（二进制性质）
 3+lowbit(3)=4  4+lowbit(4)=8......就是原来的编号加上他所管辖的区域等于后面与之相连的编号！！！
 怎么进行区间查询？
 第一步：将其拆为两个区间的差，例子：假设要查询[3,7]的和，就要拆分为sum[1,7]-sum[1,2]
 由上图，我们要求sum[1,7],结果为t[7]+t[6]+t[4],通过lowbit即可得到：
 7-lowbit(7)=6  6-lowbit(6)=4  就是原来的编号减去他所管辖的区域等于前面与之相连的编号！！！
 于是可以直接得到树状数组最重要的两个函数update()和getpre()！

**1.update函数**

```cpp
//给a[k]增加x
void update(int k, int x)
{
	for (int i = k; i <= n; i += lowbit(i))t[i] += x;
//解释：把a[k]增加x，相当于把与a[k]相关的几个区间和都要加上x。所以t[i]要加上x
}
```

**2.getprefix函数**

```cpp
//返回区间[1,k]的和
int getprefix(int k)
{
	int res = 0;
	for (int i = k; i >=1; i -= lowbit(i))res += t[i];
//以管辖区间为单位依次向前加上t[i]!!!就返回的是区间[1,k]的和！
}
```

#### 四，例题详解

例题1：蓝桥杯官网——殷老师排队

**问题描述**

体育课上，殷老师正在给学生们排队，排完队后他发现这些学生有些不同。每个学生都有一个魅力值 ai 和愉悦值 bi，愉悦值的计算公式如下：

![759f7254cffe15aca94ae5a5ee154026](D:\i_love_qq\Tencent Files\3215763265\nt_qq\nt_data\Pic\2026-05\Ori\759f7254cffe15aca94ae5a5ee154026.png)

作为一名优秀的教师他一眼就可以看出学生们的魅力值，但随着时间的推移魅力值可能会发生变化，所以愉悦值也会发生变化。在排队的过程中会有 n 个事件，这 n 个事件共分为两种情况：

第 x 个学生的魅力值变为 y。
殷老师想查看第 x 个学生的愉悦值。
殷老师太忙了，所以你可以帮他计算某个学生的愉悦值吗？

**输入格式**
第一行包含两个整数 n,m，表示学生的个数和事件的个数。

第二行包含 n 个数表示每个学生的魅力值。

之后每一个操作的开头都输入一个数字 op 表示事件的类型，如果 op=1 则输入两个整数 x,z 表示将第 x 个学生的魅力值修改为 z；若 op=2 则输入一个整数 x 表示询问从第 x 个学生的愉悦值。

**输出格式**
对于每个操作 2 输出一个数字 ans 表示学生的愉悦值。

**数据规模**

对于所有评测数据，1≤n,m≤10^5，1≤op≤2，1≤x≤n，0≤z≤10^9。

**代码详解！**

```cpp
#include <iostream>
using namespace std;
using ll = long long;
const int N = 1e5 + 9;
ll a[N], t[N], n, m;
//首先，可以将式子转换：
//bi=(i-1-1+1)ai-sigma(j=1 j=i-1)aj+sigma(j=i+1 j=n)aj-(n-i-1+1)ai
//bi=(2i-n-1)ai-sigma(j=1 j=i-1)aj+sigma(j=i+1 j=n)aj
int lowbit(int x)
{
    return x & -x;
}
void update(int k, ll x)//单点修改,将a[k]加上x
{
    a[k] += x;
    for (int i = k; i <= n; i += lowbit(i))t[i] += x;
}
ll getprefix(int k)//求区间[1,k]的和
{
    ll res = 0;
    for (int i = k; i >= 1; i -= lowbit(i))res += t[i];
    return res;
}
ll getsum(int l, int r)//求区间[l,r]的和
{
    return getprefix(r) - getprefix(l - 1);
}
ll b(int i)//求愉悦值
{
    return (2 * i - n - 1) * a[i] - getsum(1, i - 1) + getsum(i + 1, n);
}
 
 
int main()
{
    ios::sync_with_stdio(0), cin.tie(0), cout.tie(0);
    cin >> n >> m;
    for (int i = 1; i <= n; i++)
    {
        int x; cin >> x;
        update(i, x);
        //cin>>a[i];update(i,a[i]);
    }
    while (m--)
    {
        int op; cin >> op;
        if (op == 1)
        {
            ll x, y; cin >> x >> y;
            update(x, -a[x] + y);//将a[x]加上-a[x]+y,即将a[x]变成y
        }
        else
        {
            int x; cin >> x;
            cout << b(x) << '\n';
        }
    }
    return 0;
}
///若改用直接输入数组的形式，则太麻烦了，还不如前者方便
#include <iostream>
using namespace std;
using ll = long long;
const int N = 1e5 + 9;
ll a[N], t[N], n, m, g[N];
//首先，可以将式子转换：
//bi=(i-1-1+1)ai-sigma(j=1 j=i-1)aj+sigma(j=i+1 j=n)aj-(n-i-1+1)ai
//bi=(2i-n-1)ai-sigma(j=1 j=i-1)aj+sigma(j=i+1 j=n)aj
int lowbit(int x)
{
    return x & -x;
}
void update(int k, ll x) // 单点修改，将a[k]设为x
{
    g[k] += x;             // 更新a[k]
    for (int i = k; i <= n; i += lowbit(i)) t[i] += x;  // 更新树状数组
}
ll getprefix(int k)//求区间[1,k]的和
{
    ll res = 0;
    for (int i = k; i >= 1; i -= lowbit(i))res += t[i];
    return res;
}
ll getsum(int l, int r)//求区间[l,r]的和
{
    return getprefix(r) - getprefix(l - 1);
}
ll b(int i)//求愉悦值
{
    return (2 * i - n - 1) * g[i] - getsum(1, i - 1) + getsum(i + 1, n);
}
 
 
int main()
{
    ios::sync_with_stdio(0), cin.tie(0), cout.tie(0);
    cin >> n >> m;
    for (int i = 1; i <= n; i++)
    {
        //int x;cin>>x;
        //update(i,x);
        cin >> a[i]; update(i, a[i]);
    }
    while (m--)
    {
        int op; cin >> op;
        if (op == 1)
        {
            ll x, y; cin >> x >> y;
            update(x, y - g[x]);//将a[x]加上-a[x]+y,即将a[x]变成y
        }
        else
        {
            int x; cin >> x;
            cout << b(x) << '\n';
        }
    }
    return 0;
}
```



**例题2：23年蓝桥杯真题——异或和**
**问题描述**
给一棵含有 n 个结点的有根树，根结点为 1，编号为 i 的点有点权 ai（i∈[1,n]）。现在有两种操作，格式如下：

1 x y：该操作表示将点 x 的点权改为 y。
2 x：该操作表示查询以结点 x 为根的子树内的所有点的点权的异或和。
现有长度为 m 的操作序列，请对于每个第二类操作给出正确的结果。

**输入格式**
输入的第一行包含两个正整数 n,m，用一个空格分隔。

第二行包含 n 个整数 a1,a2,…,an，相邻整数之间使用一个空格分隔。

接下来 n−1 行，每行包含两个正整数 ui,vi，表示结点 ui 和 vi 之间有一条边。

接下来 m 行，每行包含一个操作。

**输出格式**
输出若干行，每行对应一个查询操作的答案。

评测用例规模与约定
对于 30% 的评测用例，n,m≤1000；对于所有评测用例，1≤n,m≤100000，0≤ai,y≤100000，1≤ui,vi,x≤n。

代码详解！
方法一：树状数组

```cpp
#include <iostream>
#include <vector>
using ll=long long;
using namespace std;
const int N=1e5+9;
ll a[N],t[N],idx[N],dfn[N],sz[N];
vector<int>g[N];
int n,m,tot=0;
 
int lowbit(int x)
{
  return x & -x;
}
 
void update(int k,int x)
{
  for(int i=k;i<=n;i+=lowbit(i)) t[i]^=x;
}
 
int query(int k)
{
  int res=0;
  for(int i=k;i>0;i-=lowbit(i)) res^=t[i];
  return res;
}
 
void dfs(int x,int fa)
{
  dfn[x]=++tot;
  idx[dfn[x]]=x;
  sz[x]=1;
  for(const auto&y:g[x])
  {
    if(y==fa) continue;
    dfs(y,x);
    sz[x]+=sz[y];
  }
}
 
int main()
{
	int q; cin >> n >> q;
	for (int i = 1; i <= n; i++)cin >> a[i];
	for (int i = 1; i < n; i++)
	{
		int u, v; cin >> u >> v;
		g[u].push_back(v), g[v].push_back(u);
	}
	dfs(1, 0);
	for (int i = 1; i <= n; i++)update(dfn[i], a[i]);
	while (q--)
	{
		int op; cin >> op;
		if (op == 1)//更新x为y
		{
			int x, y; cin >> x >> y;
			int val = query(dfn[x]) ^ query(dfn[x] - 1);
			//在初始状态（未进行任何更新操作时），query(dfn[x]) ^ query(dfn[x] - 1) 等于 a[x]；
			//	但在经过更新操作后，它等于节点 x 当前的最新值（而非初始的 a[x]）！！！！！！
			
			//val 表示的是 DFS 序中某一点的当前点权值
			/*query(dfn[x]) 返回区间 [1, dfn[x]] 的异或和。
	  query(dfn[x]-1) 返回区间 [1, dfn[x]-1] 的异或和。
	  两者异或后，得到的 val 就是位置 dfn[x] 对应的点权（即节点 x 的当前值）。*/
			update(dfn[x], val ^ y);//这一步的意思就是将dfn[x]所代表的点权（就是val）在和val^y进行异或运算
			//val^vla^y=0^y=y，至此，val被替换成y！！！
		}
		else//求异或和
		{
			int x; cin >> x;
			int l = dfn[x], r = dfn[x] + sz[x] - 1;
			int ans = query(r) ^ query(l - 1);//类似prefix
			//ans表示l到r的异或和
			/*异或（XOR，符号为 ^）具有以下关键性质：
	  交换律：a ^ b = b ^ a
	  结合律：(a ^ b) ^ c = a ^ (b ^ c)
	  自反性：a ^ a = 0（任何数异或自身为 0）
	  单位元：a ^ 0 = a（任何数异或 0 等于自身）*/
	  //定义 prefix[i] 为前 i 个元素的异或和：
	  //prefix[i] = a[1] ^ a[2] ^ ... ^ a[i]
	  //则区间 [l, r] 的异或和可表示为：
	  //a[l] ^ a[l+1] ^ ... ^ a[r] = prefix[r] ^ prefix[l-1]
	  //前面的1到l-1部分由交换律a[i]^a[i]=0,都抵消了
			cout << ans << '\n';
		}
	}
	return 0;
}
```



##### 

### 2.3.3 线段树

#### 线段树模板

线段树是一颗二叉树

线段树可以在 logN 的时间内进行区间查询与区间修改 叶子节点记录元素本身，非叶子节点记录对应区间内的元素统计值

![page image](E:/桌面/acm相关/模板/模板_assets/page_099_111.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_100_113.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_100_112.png)

#### 区间查询

从节点 1开始，每次查看当前节点对应的区间 [L, R] 是否被更新区间 [x, y] 完全覆盖，如果有则返回 该区间的元素统计值，否则继续向左右子节点继续查询

#### 线段树代码

```cpp
#include<bits/stdc++.h>
using namespace std;
#define int long long
#define N 500005
#define lc p<<1
#define rc p<<1|1
int w[N],n;
struct node{
    int l,r,sum,add;
}tr[4*N];
void build(int p,int l,int r){
    //tr[p].l=l,tr[p].r=r,tr[p].sum=w[l];
    tr[p]={l,r,w[l],0};
    if (l == r) return;  
    int m=l+r>>1;
    build(lc,l,m);
    build(rc,m+1,r);
    tr[p].sum=tr[lc].sum+tr[rc].sum;
    
}
void pushup(int p){
    tr[p].sum=tr[lc].sum+tr[rc].sum;
}
void pushdown(int p){
    if(!tr[p].add)return; 
    tr[lc].sum+=(tr[lc].r-tr[lc].l+1)*tr[p].add;
    tr[rc].sum+=(tr[rc].r-tr[rc].l+1)*tr[p].add;
    tr[lc].add+=tr[p].add;
    tr[rc].add+=tr[p].add;
    tr[p].add=0;
}
void update(int p,int x,int y,int k){
    if(tr[p].l>=x&&tr[p].r<=y){
        tr[p].sum+=(tr[p].r-tr[p].l+1)*k;
        tr[p].add+=k;
        return;
    }
    int m=tr[p].l+tr[p].r>>1;
    pushdown(p);
    if(x<=m)update(lc,x,y,k);
    if(y>m)update(rc,x,y,k);
    pushup(p);
}

int query(int p,int x,int y){
    if(x<=tr[p].l&&tr[p].r<=y){
        return tr[p].sum;
    }
    int m=tr[p].l+tr[p].r>>1;
    pushdown(p);
    int sum=0;
    if(x<=m)sum+=query(lc,x,y);
    if(y>m) sum+=query(rc,x,y);
    return sum;
    
}

signed main(){
    int n,m;
    cin>>n>>m;
    for(int i=1;i<=n;i++)cin>>w[i];
    build(1,1,n);
    while(m--){
        int q;
        cin>>q;
        if(q==1){
             int x,y,k;
             cin>>x>>y>>k;
            update(1,x,y,k);
        }else{
            int x,y;
            cin>>x>>y;
            cout<<query(1,x,y)<<endl;
        }
    }
}
```







## 2.4 图论类✅️

### 最短路：

```cpp
#include <bits/stdc++.h>
#define endl "\n"
#define int long long 
using namespace std;
const int N=1e6+5;
struct edge{
    int v,w;
};
vector<edge> e[N];
int d[N],vis[N];
int n,m,s;

priority_queue<pair<int,int>> q;

void dijkstra(int s){
    for(int i=0;i<=n;i++)d[i]=1<<30;
    d[s]=0;
    q.push({0,s});
    while(!q.empty()){
        auto t=q.top();q.pop();
        int u=t.second;
        if(vis[u])continue;
        vis[u]=1;
        for(auto ed:e[u]){
            int v=ed.v,w=ed.w;
            if(d[v]>d[u]+w){
                d[v]=d[u]+w;
                q.push({-d[v],v});
            }
        }
    }
}

signed main(){
    ios::sync_with_stdio(0);cin.tie(0);cout.tie(0);
   
   cin>>n>>m>>s;
   for (int i=1;i<=m;i++){
        int x,y,w;
        cin>>x>>y>>w;
        e[x].push_back({y,w});
    }
    dijkstra(s);
    for(int i=1; i<=n;i++)
        printf("%d ",d[i]);
}
```

```cpp
#include<bits/stdc++.h>
using namespace std;
#define endl '\n'
#define int long long
const int N=1e4+5;
const int inf=(1<<31)-1;
struct edge{int v,w;};
vector<edge>e[N];
int d[N],vis[N],pre[N];
int n,m,s;
priority_queue<pair<int,int>>q;
void dijkstra(int s){
    for(int i=0;i<=n;i++)d[i]=inf;
    d[s]=0;
    q.push({0,s});
    while(q.size()){
        auto t=q.top(); q.pop();
        int u=t.second;
        if(vis[u])continue;
        vis[u]=1;
        for(auto ed:e[u]){
            int v=ed.v,w=ed.w;
            if(d[u]+w<d[v]){
                d[v]=d[u]+w;
               // pre[v]=u;路径
                q.push({-d[v],v});
            }
        }
    }
}
//路径回溯
// void dfs_path(int u){
//     if(u==s){
//         cout<<u<<" ";
//         return;
//     }
//     dfs_path(pre[u]);
//     cout<<u<<" ";
// }

signed main() {
    ios::sync_with_stdio(0); cin.tie(0); cout.tie(0);
   
    cin>>n>>m>>s;
    for(int i=0;i<m;i++){
      int x,y,c;
      cin>>x>>y>>c;
      e[x].push_back({y,c});
    }
    dijkstra(s);
    for(int i=1;i<=n;i++){
        // if(d[i]==inf)cout<<(1<<31)-1<<" ";
         cout<<d[i]<<" ";
    }
    return 0;
}
```



### 最小生成树：

```cpp
#include <bits/stdc++.h>
using namespace std;
const int N=1e6+5;
struct node{
  int u,v,dis;  
}ed[N];

int w[N];
bool cmp(node x,node y){
    return x.dis<y.dis;
}

int find(int i){
    if(w[i]==i)return i;
    else return w[i]=find(w[i]);
}

void Kruskal(int n,int m){
    int ans=0;
    int num=0;
    
    for (int i=1;i<=m;i++){
        int e=find(ed[i].u);
        int f=find(ed[i].v);
        if(e!=f){
            w[e]=f;
            ans=max(ans,ed[i].dis);
            num++;
            if(num==n-1)break;
        }
    }
    cout<<num<<" "<<ans;
    
}

int main(){
    int n,m;
    cin>>n>>m;
    for (int i=0;i<=n;i++)w[i]=i;
    
    for (int i=1;i<=m;i++){
        cin>>ed[i].u>>ed[i].v>>ed[i].dis;
    }
    sort(ed+1,ed+m+1,cmp);
    Kruskal(n,m);
    
}
```

```cpp
#include<bits/stdc++.h>
using namespace std;
#define endl '\n'
#define int long long
const int N=2e5+5;
struct edge{
    int u,v,w;
    bool operator<(const edge &t)const
    {return w < t.w;}
}e[N];
int fa[N],ans,cnt,n,m;
int find(int x){
    if(fa[x]==x)return x;
    return fa[x]=find(fa[x]);
}
bool kruskal(){
    sort(e,e+m);
    for(int  i=1;i<=n;i++)fa[i]=i;
    for(int i=0;i<m;i++){
        int x=find(e[i].u);
        int y=find(e[i].v);
        if(x!=y){
            fa[x]=y;
            ans+=e[i].w;
            cnt++;
        }
    }
    return cnt==n-1;
}
signed main() {
    ios::sync_with_stdio(0); cin.tie(0); cout.tie(0);
    
   
       cin>>n>>m;
       for(int i=0;i<m;i++){
        cin>>e[i].u>>e[i].v>>e[i].w;
       }
       if(kruskal()){
         cout<<ans<<endl;
       }else{
        cout<<"orz"<<endl;
       }
    
}
```



### 树链剖分

定义路径权值为路径的价值和，对树进行长链剖分。容易发现，贪心的算法流程等价于每次选择权值最大的一条长链，因此答案即为前 k大的长链的权值之和，可以做到 O(n)。

```c++
#include <bits/stdc++.h>
#define ll long long
#define endl "\n"
using namespace std;
set<ll> tree[200000 + 5];
ll v[200000 + 5], x[200000 + 5], cnt = 0;
ll du[200000 + 5];
ll dfs(int u)
{
    ll son = 0, res = 0;
    for (auto i : tree[u])
    {
        ll now = dfs(i);
        if (now > res)
        {
            if (son)
            {
                cnt++;
                x[cnt] = res;
            }
            son = i;
            res = now;
        }
        else
        {
            cnt++;
            x[cnt] = now;
        }
    }
    return res + v[u];
}
int main(){
    ll n, k;
    cin >> n >> k;
    for (int i = 1; i <= n; i++)
        cin >> v[i];
    for (int i = 1; i < n; i++)
    {
        int u, v;
        cin >> u >> v;
        tree[u].insert(v);
        du[v]++;
    }
    ll s = 1;
    for (int i = 1; i <= n; i++)
    {
        if (!du[i])
        {
            s = i;
            break;
        }
    }
    ll now = dfs(s);
    cnt++;
    x[cnt] = now;
    sort(x + 1, x + 1 + cnt, greater<ll>());
    ll ans = 0;
    for (ll i = 1; i <= min(k, cnt); i++)
        ans += x[i];
    cout << ans << endl;
}
```

### lca树链

```c++
#include <bits/stdc++.h>
#define endl "\n"
using namespace std;
const int N=5*1e5+5;

vector<int> e[N];
int fa[N],dep[N],son[N],sz[N];
int top[N];

void dfs1(int u,int father){
    fa[u]=father,dep[u]=dep[father]+1,sz[u]=1;
    for (int v:e[u]){
        if (v==father)continue;
        dfs1(v,u);
        sz[u]+=sz[v];
        if (sz[son[u]]<sz[v])son[u]=v;
    }
}

void dfs2(int u,int t){
    top[u]=t;
    if (!son[u])return ;
    dfs2(son[u],t);
    for (int v:e[u]){
        if (v==fa[u]||v==son[u])continue;
        dfs2(v,v);
    }
}

int LCA(int u,int v){
    while(top[u]!=top[v]){
        if (dep[top[u]]<dep[top[v]])swap(u,v);
        u=fa[top[u]];
    }
    return dep[u]<dep[v]?u:v;
}

int main(){
    int n,m,s,a,b;
    ios::sync_with_stdio(0);cin.tie(0);cout.tie(0);
    cin>>n>>m>>s;
    for (int i=1;i<=n-1;i++){
        cin>>a>>b;
        e[a].push_back(b);
        e[b].push_back(a);
    }
    dfs1(s,0);
    dfs2(s,s);
    for (int i=1;i<=m;i++){
        cin>>a>>b;
        cout <<LCA(a,b)<<endl;
    }
}
```

### 最短路不固定起点的Floyd

```cpp
#include<bits/stdc++.h>
using namespace std;
#define endl '\n'
#define int long long
const int N=200+5;
const int inf=1e10+5;
int d[N][N],p[N][N],n,m;
void floyd(){
    for(int k=1;k<=n;k++){
        for(int i=1;i<=n;i++){
            for(int j=1;j<=n;j++){
                if(d[i][j]>d[i][k]+d[k][j]){
                    d[i][j]=d[i][k]+d[k][j];
                    p[i][j]=k;//记录插点
                }
            }
        }
    }
}
void path(int i,int j){
    if(p[i][j]==0)return;
    int k=p[i][j];
    path(i,k);
    cout<<k<<"->";
    path(k,j);
}
signed main() {
    ios::sync_with_stdio(0); cin.tie(0); cout.tie(0);
    cin>>n>>m;
    for(int i=1;i<=n;i++){
        for(int j=1;j<=n;j++){
             if(i==j)d[i][j]=0;
             else d[i][j]=inf;
        }
    }
    for(int i=0;i<m;i++){
        int x,y,c;//起点，终点，边权
        cin>>x>>y>>c;
        d[x][y]=c;
    }
    floyd();
    for(int i=1;i<=n;i++){
        for(int j=1;j<=n;j++){
            cout<<d[i][j]<<endl;
            cout<<i<<"->";
            path(i,j);
            cout<<j<<endl;
        }
      
    }
  
    
    return 0;
}
```



### 2.4.1拓扑排序

#### 拓扑排序模板

```cpp
// Kahn算法 O(n)
#include <bits/stdc++.h>
using namespace std;
const int N = 100010;
int n, m, a, b;
vector<int> e[N], tp;
int din[N];
bool toposort()
{
    queue<int> q;
    for (int i = 1; i <= n; i++)
        if (din[i] == 0)
            q.push(i);
    while (q.size())
    {
        int x = q.front();
        q.pop();
        tp.push_back(x);
        for (auto y : e[x])
        {
            if (--din[y] == 0)
                q.push(y);
        }
    }
    return tp.size() == n;
}
int main()
{
    cin >> n >> m;
    for (int i = 0; i < m; i++)
    {
        cin >> a >> b;
        e[a].push_back(b);
        din[b]++;
    }
    if (!toposort())
        puts("-1");
    else
        for (auto x : tp)
            printf("%d ", x);
    return 0;
}
```



#### 例题

有一个王国，境内共有 n 座城市，由 \(n-1\) 条道路相连，**所有道路长度均为 1**。

国王打算选出一片区域作为王国首都，该区域必须恰好包含 k 座**互相连通**的城市（即首都所在连通块的城市数量严格为 k）。

为凸显首都的重要性，国王希望让**所有城市的权值中的最大值尽可能小**。

我们对城市的权值定义如下：一座城市的权值，是该城市到**首都区域内任意一座城市**的最短距离。两座城市间的距离，指二者最短路径的总长度。

```cpp
#include <bits/stdc++.h>
// #define ll long long
// #define endl "\n"
using namespace std;
int n, k;
vector<int> g[100005];
queue<int> q;
bool vis[100005];
int du[100005];
int ans[100000 + 5];
int main()
{
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    cout.tie(0);
    cin >> n >> k;
    for (int i = 1; i < n; ++i)
    {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        g[v].push_back(u);
        ++du[v];
        ++du[u];
    }
    for (int i = 1; i <= n; ++i)
    {
        if (du[i] == 1)
            q.push(i);
    }
    int sm = n;
    while (q.size() and sm > k)
    {
        int u = q.front();
        q.pop();
        if (vis[u])
            continue;
        else
            vis[u] = 1;
        int nxt = -1;
        du[u]--;
        if (!du[u])
            sm--;
        for (auto i : g[u])
        {
            if (du[i])
            {
                du[i]--;
                if (du[i] == 1)
                    nxt = i;
                ans[i] = ans[u] + 1;
            }
        }
        if (nxt != -1)
            q.push(nxt);
    }
    //     if (k == n) cout << 0 << endl;
    cout << *max_element(ans + 1, ans + 1 + n) << endl;
}
```

### 2.4.2最短路

#### Dijkstra模板

```cpp
// 堆优化Dijkstra
#include <bits/stdc++.h>
using namespace std;

const int N = 100010;
int n, m, s, a, b, c;

struct edge {
    int v, w;
};

vector<edge> e[N];
int d[N], vis[N];

void dijkstra(int s) {
    memset(d, 0x3f, sizeof d);
    d[s] = 0;
    
    priority_queue<pair<int, int>> q;
    q.push({0, s});
    
    while (q.size()) {
        auto t = q.top();
        q.pop();
        
        int u = t.second;
        if (vis[u]) continue;   // 已确定最短路，跳过
        vis[u] = 1;             // 标记u已出队
        
        for (auto ed : e[u]) {
            int v = ed.v, w = ed.w;
            if (d[v] > d[u] + w) {
                d[v] = d[u] + w;
                q.push({-d[v], v});  // 大根堆模拟小根堆
            }
        }
    }
}

int main() {
    cin >> n >> m >> s;
    for (int i = 0; i < m; i++) {
        cin >> a >> b >> c;
        e[a].push_back({b, c});
    }
    
    dijkstra(s);
    
    for (int i = 1; i <= n; i++) {
        printf("%d ", d[i]);
    }
    
    return 0;
}
```

#### BFS_SPFA 判负环 模板

```cpp
// BFS_spfa 判负环 530ms
#include <bits/stdc++.h>
using namespace std;
const int inf = 0x3f3f3f3f;
const int N = 2010, M = 6010;
int n, m;
int to[M], ne[M], w[M], h[N], tot;
int d[N], cnt[N], vis[N];
void add(int a, int b, int c)
{
    to[++tot] = b;
    w[tot] = c;
    ne[tot] = h[a];
    h[a] = tot;
}
bool spfa()
{ // 判负环
    memset(d, 0x3f, sizeof d);
    memset(vis, 0, sizeof vis);
    memset(cnt, 0, sizeof cnt);
    queue<int> q;
    q.push(1);
    vis[1] = 1;
    d[1] = 0;
    while (q.size())
    {
        int u = q.front();
        q.pop();
        vis[u] = 0;
        for (int i = h[u]; i; i = ne[i])
        {
            int v = to[i];
            if (d[v] > d[u] + w[i])
            {
                d[v] = d[u] + w[i];
                cnt[v] = cnt[u] + 1;
                if (cnt[v] >= n)
                    return 1; // 判边数
                if (!vis[v])
                    q.push(v), vis[v] = 1;
            }
        }
    }
    return 0;
}
int main()
{
    int T;
    scanf("%d", &T);
    while (T--)
    {
        tot = 0;
        memset(h, 0, sizeof(h));
        scanf("%d%d", &n, &m);
        for (int i = 1; i <= m; i++)
        {
            int u, v, w;
            scanf("%d%d%d", &u, &v, &w);
            add(u, v, w);
            if (w >= 0)
                add(v, u, w);
            ;
        }
        puts(spfa() ? "YES" : "NO");
    }
    return 0;
}
```



#### FLoyd 模板

```cpp
void floyd()
{
    for (int k = 1; k <= n; k++)
        for (int i = 1; i <= n; i++)
            for (int j = 1; j <= n; j++)
                d[i][j] = min(d[i][j], d[i][k] + d[k][j]);
}
```

#### Johnson全源最短路 模板

给定一个包含 n 个结点和 m 条带权边的有向图，求所有点对间的最短路径长度，一条路径的长度 定义为这条路径上所有边的权值和。

```cpp
#include <bits/stdc++.h>
#define N 30010
#define INF 1000000000
using namespace std;

int n, m, a, b, c;
struct edge {
    int v, w;
};

vector<edge> e[N];
int vis[N], cnt[N];
long long h[N], d[N];

void spfa() {
    queue<int> q;
    memset(h, 63, sizeof h);
    memset(vis, false, sizeof vis);
    h[0] = 0, vis[0] = 1;
    q.push(0);

    while (q.size()) {
        int u = q.front();
        q.pop();
        vis[u] = 0;

        for (auto ed : e[u]) {
            int v = ed.v, w = ed.w;
            if (h[v] > h[u] + w) {
                h[v] = h[u] + w;
                cnt[v] = cnt[u] + 1;
                if (cnt[v] > n) {
                    printf("-1\n");
                    exit(0);
                }
                if (!vis[v]) {
                    q.push(v);
                    vis[v] = 1;
                }
            }
        }
    }
}

void dijkstra(int s) {
    priority_queue<pair<long long, int>> q;
    for (int i = 1; i <= n; i++)
        d[i] = INF;
    memset(vis, false, sizeof vis);
    d[s] = 0;
    q.push({0, s});

    while (q.size()) {
        int u = q.top().second;
        q.pop();

        if (vis[u])
            continue;
        vis[u] = 1;

        for (auto ed : e[u]) {
            int v = ed.v, w = ed.w;
            if (d[v] > d[u] + w) {
                d[v] = d[u] + w;
                if (!vis[v])
                    q.push({-d[v], v});
            }
        }
    }
}

int main() {
    cin >> n >> m;
    for (int i = 0; i < m; i++) {
        cin >> a >> b >> c;
        e[a].push_back({b, c});
    }

    for (int i = 1; i <= n; i++)
        e[0].push_back({i, 0}); // 加虚拟边

    spfa();

    for (int u = 1; u <= n; u++)
        for (auto &ed : e[u])
            ed.w += h[u] - h[ed.v]; // 构造新边

    for (int i = 1; i <= n; i++) {
        dijkstra(i);
        long long ans = 0;
        for (int j = 1; j <= n; j++) {
            if (d[j] == INF)
                ans += (long long)j * INF;
            else
                ans += (long long)j * (d[j] + h[j] - h[i]);
        }
        printf("%lld\n", ans);
    }

    return 0;
}
```

### 2.4.3 生成树

#### Prim模板

```cpp
#include <bits/stdc++.h>
#define inf 1e9
using namespace std;

int n, m, a, b, c, ans, cnt;
const int N = 5010;

struct edge
{
    int v, w;
};

vector<edge> e[N];
int d[N], vis[N];

bool prim(int s)
{
    for (int i = 0; i <= n; i++)
        d[i] = inf;
    d[s] = 0;

    for (int i = 1; i <= n; i++)
    {
        int u = 0;
        for (int j = 1; j <= n; j++)
        {
            if (!vis[j] && d[j] < d[u])
                u = j;
        }
        vis[u] = 1; // 标记u已出圈
        ans += d[u];
        if (d[u] != inf)
            cnt++;

        for (auto ed : e[u])
        {
            int v = ed.v, w = ed.w;
            if (d[v] > w)
                d[v] = w;
        }
    }
    return cnt == n;
}

int main()
{
    cin >> n >> m;
    for (int i = 0; i < m; i++)
    {
        cin >> a >> b >> c;
        e[a].push_back({b, c});
        e[b].push_back({a, c});
    }

    if (!prim(1))
        puts("orz");
    else
        printf("%d\n", ans);
    return 0;
}

///////////////////Heap-Prim
#include <cstring>
#include <iostream>
#include <algorithm>
#include <queue>
#define inf 1e9
using namespace std;

const int N = 5010;
int n, m, a, b, c, ans, cnt;

struct edge
{
    int v, w;
};

vector<edge> e[N];
int d[N], vis[N];
priority_queue<pair<int, int>> q;

bool prim(int s)
{
    for (int i = 0; i <= n; i++)
        d[i] = inf;
    d[s] = 0;
    q.push({0, s});

    while (q.size())
    {
        int u = q.top().second;
        q.pop();
        if (vis[u])
            continue; // 再出队跳过
        vis[u] = 1; // 标记u已出队
        ans += d[u];
        cnt++;

        for (auto ed : e[u])
        {
            int v = ed.v, w = ed.w;
            if (d[v] > w)
            {
                d[v] = w;
                q.push({-d[v], v}); // 大根堆
            }
        }
    }
    return cnt == n;
}

int main()
{
    cin >> n >> m;
    for (int i = 0; i < m; i++)
    {
        cin >> a >> b >> c;
        e[a].push_back({b, c});
        e[b].push_back({a, c});
    }

    if (!prim(1))
        puts("orz");
    else
        printf("%d\n", ans);
    return 0;
}
```

#### Kruskal模板

```cpp
#include <bits/stdc++.h>
using namespace std;

const int N = 200006;
int n, m;

struct edge {
    int u, v, w;
    bool operator<(const edge &t) const {
        return w < t.w;
    }
} e[N];

int fa[N], ans, cnt;

int find(int x) {
    if (fa[x] == x)
        return x;
    return fa[x] = find(fa[x]);
}

bool kruskal() {
    sort(e, e + m);
    for (int i = 1; i <= n; i++)
        fa[i] = i;

    for (int i = 0; i < m; i++) {
        int x = find(e[i].u);
        int y = find(e[i].v);
        if (x != y) {
            fa[x] = y;
            ans += e[i].w;
            cnt++;
        }
    }
    return cnt == n - 1;
}

int main() {
    cin >> n >> m;
    for (int i = 0; i < m; i++)
        cin >> e[i].u >> e[i].v >> e[i].w;

    if (!kruskal())
        puts("orz");
    else
        printf("%d\n", ans);

    return 0;
}
```

### 2.4.4 最近公共祖先(LCA)

#### 倍增LCA模板

```cpp
// O((n+m)logn) 邻接表稍微快一点
#include <bits/stdc++.h>
using namespace std;
const int N = 500005;
int n, m, s;
vector<int> e[N];
int dep[N], fa[N][22];
void dfs(int x, int f)
{ // 树增dep,fa
    dep[x] = dep[f] + 1;
    fa[x][0] = f;
    // x上面2,4,8...的祖先fa
    for (int i = 1; i <= 20; i++)
        fa[x][i] = fa[fa[x][i - 1]][i - 1];
    for (int y : e[x])
        if (y != f)
            dfs(y, x);
}
int lca(int x, int y)
{ // 树增lca
    if (dep[x] < dep[y])
        swap(x, y);
    // x先大步后小步向上跳，直到与y同层
    for (int i = 20; ~i; i--)
        if (dep[fa[x][i]] >= dep[y])
            x = fa[x][i];
    if (x == y)
        return y;
    // x,y一起向上跳，直到lca的下面
    for (int i = 20; ~i; i--)
        if (fa[x][i] != fa[y][i])
            x = fa[x][i], y = fa[y][i];
    return fa[x][0];
}
int main()
{
    scanf("%d%d%d", &n, &m, &s);
    int a, b;
    for (int i = 1; i < n; i++)
    {
        scanf("%d%d", &a, &b);
        e[a].push_back(b);
        e[b].push_back(a);
    }
    dfs(s, 0);
    while (m--)
        scanf("%d%d", &a, &b), printf("%d\n", lca(a, b));
}
```



#### Tarjan算法求LCA 模板 (离线算法)

```cpp
// O(n+m)
#include <bits/stdc++.h>
using namespace std;

const int N = 500005, M = 2 * N;
int n, m, s, a, b;

vector<int> e[N];
vector<pair<int, int>> query[N];
int fa[N], vis[N], ans[M];

int find(int x)
{
    if (x == fa[x])
        return x;
    return fa[x] = find(fa[x]);
}

void tarjan(int x)
{
    vis[x] = true; // 标记x已访问

    for (auto y : e[x])
    {
        if (!vis[y])
        {
            tarjan(y);
            fa[y] = x; // 回到x时指向x
        }
    }

    // 离开x时找LCA
    for (auto q : query[x])
    {
        int y = q.first, i = q.second;
        if (vis[y])
            ans[i] = find(y);
    }
}

int main()
{
    scanf("%d%d%d", &n, &m, &s);

    for (int i = 1; i < n; i++)
    {
        scanf("%d%d", &a, &b);
        e[a].push_back(b);
        e[b].push_back(a);
    }

    for (int i = 1; i <= m; i++)
    {
        scanf("%d%d", &a, &b);
        query[a].push_back({b, i});
        query[b].push_back({a, i});
    }

    for (int i = 1; i <= N; i++)
        fa[i] = i;

    tarjan(s);

    for (int i = 1; i <= m; i++)
        printf("%d\n", ans[i]);

    return 0;
}
```

#### 树链剖分求LCA 模板

```cpp
// 树链剖分 O(mlogn)
#include <bits/stdc++.h>
using namespace std;

const int N = 500010;
int n, m, s, a, b;
vector<int> e[N];
int fa[N], son[N], dep[N], siz[N], top[N];

void dfs1(int u, int f)
{ // 搞fa,son,dep
    fa[u] = f;
    siz[u] = 1;
    dep[u] = dep[f] + 1;

    for (int v : e[u])
    {
        if (v == f)
            continue;
        dfs1(v, u);
        siz[u] += siz[v];
        if (siz[son[u]] < siz[v])
            son[u] = v;
    }
}

void dfs2(int u, int t)
{ // 搞top
    top[u] = t; // 记录链头
    if (!son[u])
        return; // 无重儿子

    dfs2(son[u], t); // 搜重儿子

    for (int v : e[u])
    {
        if (v == fa[u] || v == son[u])
            continue;
        dfs2(v, v); // 搜轻儿子
    }
}

int lca(int u, int v)
{
    while (top[u] != top[v])
    {
        if (dep[top[u]] < dep[top[v]])
            swap(u, v);
        u = fa[top[u]];
    }
    return dep[u] < dep[v] ? u : v;
}

int main()
{
    scanf("%d%d%d", &n, &m, &s);

    for (int i = 1; i < n; i++)
    {
        scanf("%d%d", &a, &b);
        e[a].push_back(b);
        e[b].push_back(a);
    }

    dfs1(s, 0);
    dfs2(s, s);

    while (m--)
    {
        scanf("%d%d", &a, &b);
        printf("%d\n", lca(a, b));
    }

    return 0;
}
```

三种算法比较:

![page image](E:/桌面/acm相关/模板/模板_assets/page_145_140.png)

#### 点的距离 LCA应用 三种算法

```cpp
#include <bits/stdc++.h>
using namespace std;

const int N = 100010, h = 18;
int n, m, a, b;
vector<int> e[N];
int dep[N], fa[N][19], dis[N];

void dfs(int u, int father)
{
    dep[u] = dep[father] + 1;
    fa[u][0] = father;
    for (int i = 1; i <= h; i++)
        fa[u][i] = fa[fa[u][i - 1]][i - 1];

    for (int v : e[u])
    {
        if (v == father) continue;
        dis[v] = dis[u] + 1;
        dfs(v, u);
    }
}

int lca(int x, int y)
{
    if (dep[x] < dep[y]) swap(x, y);
    for (int i = h; i >= 0; i--)
        if (dep[fa[x][i]] >= dep[y])
            x = fa[x][i];

    if (x == y) return x;
    for (int i = h; i >= 0; i--)
        if (fa[x][i] != fa[y][i])
            x = fa[x][i], y = fa[y][i];

    return fa[x][0];
}

int main()
{
    scanf("%d", &n);
    for (int i = 1; i < n; i++)
    {
        scanf("%d%d", &a, &b);
        e[a].push_back(b);
        e[b].push_back(a);
    }

    dfs(1, 0);
    scanf("%d", &m);
    while (m--)
    {
        scanf("%d%d", &a, &b);
        int d = dis[a] + dis[b] - dis[lca(a, b)] * 2;
        printf("%d\n", d);
    }

    return 0;
}

///////////////////树链剖分
#include <iostream>
#include <cstring>
#include <algorithm>
#include <vector>
using namespace std;

const int N = 100010;
int n, m, a, b, c;
vector<int> e[N];
int dep[N], fa[N], son[N], sz[N], dis[N];
int top[N];

void dfs1(int u, int father)
{
    fa[u] = father, dep[u] = dep[father] + 1, sz[u] = 1;
    for (int v : e[u])
    {
        if (v == father) continue;
        dis[v] = dis[u] + 1;
        dfs1(v, u);
        sz[u] += sz[v];
        if (sz[son[u]] < sz[v])
            son[u] = v;
    }
}

void dfs2(int u, int t)
{
    top[u] = t;
    if (!son[u]) return;
    dfs2(son[u], t);

    for (int v : e[u])
    {
        if (v == fa[u] || v == son[u]) continue;
        dfs2(v, v);
    }
}

int lca(int x, int y)
{
    while (top[x] != top[y])
    {
        if (dep[top[x]] < dep[top[y]]) swap(x, y);
        x = fa[top[x]];
    }
    return dep[x] < dep[y] ? x : y;
}

int main()
{
    scanf("%d", &n);
    for (int i = 1; i < n; i++)
    {
        scanf("%d%d", &a, &b);
        e[a].push_back(b);
        e[b].push_back(a);
    }

    dfs1(1, 0);
    dfs2(1, 1);
    scanf("%d", &m);
    while (m--)
    {
        scanf("%d%d", &a, &b);
        int d = dis[a] + dis[b] - dis[lca(a, b)] * 2;
        printf("%d\n", d);
    }

    return 0;
}

///////////////////Tarjan 算法
#include <cstdio>
#include <cstring>
#include <iostream>
#include <algorithm>
#include <vector>
using namespace std;

typedef pair<int, int> PII;
const int N = 100010, M = N * 2;
int n, m, a, b;
vector<int> e[N];
vector<PII> query[N];
int fa[N], vis[N], dis[N];
int ans[M];

int find(int u)
{
    if (fa[u] == u) return u;
    return fa[u] = find(fa[u]);
}

void tarjan(int u)
{
    vis[u] = 1;
    for (int v : e[u])
    {
        if (vis[v]) continue;
        dis[v] = dis[u] + 1;
        tarjan(v);
        fa[v] = u;
    }

    for (auto ed : query[u])
    {
        int v = ed.first, i = ed.second;
        if (vis[v])
            ans[i] = dis[u] + dis[v] - dis[find(v)] * 2;
    }
}

int main()
{
    scanf("%d", &n);
    for (int i = 1; i < n; i++)
    {
        scanf("%d%d", &a, &b);
        e[a].push_back(b);
        e[b].push_back(a);
    }

    scanf("%d", &m);
    for (int i = 1; i <= m; i++)
    {
        scanf("%d%d", &a, &b);
        query[a].push_back({b, i});
        query[b].push_back({a, i});
    }

    for (int i = 1; i <= n; i++) fa[i] = i;
    tarjan(1);

    for (int i = 1; i <= m; i++)
        printf("%d\n", ans[i]);

    return 0;
}
```

### 2.4.5 树链剖分

#### 树链剖分模板 (轻重链剖分)

```cpp
#include <bits/stdc++.h>
using namespace std;

#define LL long long
#define lc u << 1
#define rc u << 1 | 1

const int N = 100010;
int n, m, a, b, root, P, w[N];
vector<int> e[N];
int fa[N], son[N], dep[N], siz[N];
int top[N], id[N], nw[N], tim; // 重链

struct tree {
    int l, r;
    LL add, sum;
} tr[N * 4]; // 线段树

void dfs1(int u, int f) { // 搞fa,dep,siz,son
    fa[u] = f, dep[u] = dep[f] + 1, siz[u] = 1;
    for (int v : e[u]) {
        if (v == f) continue;
        dfs1(v, u);
        siz[u] += siz[v];
        if (siz[son[u]] < siz[v])
            son[u] = v;
    }
}

void dfs2(int u, int tp) { // 搞top,id,nw
    top[u] = tp, id[u] = ++tim, nw[tim] = w[u];
    if (!son[u]) return;
    dfs2(son[u], tp);
    for (int v : e[u]) {
        if (v == fa[u] || v == son[u]) continue;
        dfs2(v, v);
    }
}

void pushup(int u) {
    tr[u].sum = tr[lc].sum + tr[rc].sum;
}

void pushdown(int u) {
    if (tr[u].add) {
        tr[lc].sum += tr[u].add * (tr[lc].r - tr[lc].l + 1);
        tr[rc].sum += tr[u].add * (tr[rc].r - tr[rc].l + 1);
        tr[lc].add += tr[u].add;
        tr[rc].add += tr[u].add;
        tr[u].add = 0;
    }
}

void build(int u, int l, int r) { // 构建线段树
    tr[u] = {l, r, 0, nw[r]};
    if (l == r) return;
    int mid = l + r >> 1;
    build(lc, l, mid), build(rc, mid + 1, r);
    pushup(u);
}

void change(int u, int l, int r, int k) { // 线段树修改
    if (l <= tr[u].l && tr[u].r <= r) {
        tr[u].add += k;
        tr[u].sum += k * (tr[u].r - tr[u].l + 1);
        return;
    }
    pushdown(u);
    int mid = tr[u].l + tr[u].r >> 1;
    if (l <= mid) change(lc, l, r, k);
    if (r > mid) change(rc, l, r, k);
    pushup(u);
}

void change_path(int u, int v, int k) { // 修改路径
    while (top[u] != top[v]) {
        if (dep[top[u]] < dep[top[v]])
            swap(u, v);
        change(1, id[top[u]], id[u], k);
        u = fa[top[u]];
    }
    if (dep[u] < dep[v])
        swap(u, v);
    change(1, id[v], id[u], k); // 最后一段
}

void change_tree(int u, int k) { // 修改子树
    change(1, id[u], id[u] + siz[u] - 1, k);
}

LL query(int u, int l, int r) { // 线段树查询
    if (l <= tr[u].l && tr[u].r <= r)
        return tr[u].sum;
    pushdown(u);
    int mid = tr[u].l + tr[u].r >> 1;
    LL res = 0;
    if (l <= mid) res += query(lc, l, r);
    if (r > mid) res += query(rc, l, r);
    return res;
}

LL query_path(int u, int v) { // 查询路径
    LL res = 0;
    while (top[u] != top[v]) {
        if (dep[top[u]] < dep[top[v]])
            swap(u, v);
        res += query(1, id[top[u]], id[u]);
        u = fa[top[u]];
    }
    if (dep[u] < dep[v])
        swap(u, v);
    res += query(1, id[v], id[u]); // 最后一段
    return res;
}

LL query_tree(int u) { // 查询子树
    return query(1, id[u], id[u] + siz[u] - 1);
}

int main() {
    scanf("%d%d%d%d", &n, &m, &root, &P);
    for (int i = 1; i <= n; i++)
        scanf("%d", &w[i]);
    for (int i = 0; i < n - 1; i++) {
        scanf("%d%d", &a, &b);
        e[a].push_back(b);
        e[b].push_back(a);
    }

    dfs1(root, 0);
    dfs2(root, root); // 把树拆成链
    build(1, 1, n); // 用链建线段树

    while (m--) {
        int t, u, v, k;
        scanf("%d%d", &t, &u);
        if (t == 1) {
            scanf("%d%d", &v, &k);
            change_path(u, v, k);
        } else if (t == 3) {
            scanf("%d", &k);
            change_tree(u, k);
        } else if (t == 2) {
            scanf("%d", &v);
            printf("%d\n", query_path(u, v) % P);
        } else {
            printf("%d\n", query_tree(u) % P);
        }
    }
    return 0;
}
```



#### 长链

![image-20260529212410759](C:\Users\32157\AppData\Roaming\Typora\typora-user-images\image-20260529212410759.png)

```cpp
// 长链剖分+树形DP
#include <bits/stdc++.h>
using namespace std;
const int N = 1e6 + 5;
vector<int> e[N];
int n, son[N], len[N];
int buf[N], *f[N], *p = buf, ans[N];
// f[x][i]:在x子树内与x的距离为i的节点数

void dfs(int x, int fa) { // 长链剖分
    for (int y : e[x]) {
        if (y == fa)
            continue;
        dfs(y, x);
        if (len[son[x]] < len[y])
            son[x] = y;
    }
    len[x] = len[son[x]] + 1;
}

void DP(int x, int fa) { // 树形DP
    f[x][0] = 1;
    if (son[x]) {
        f[son[x]] = f[x] + 1; // 共享内存,f[son[x]][i]会被自动保存到f[x][i+1]
        DP(son[x], x);
        ans[x] = ans[son[x]] + 1; // 继承答案
    }
    for (int y : e[x]) {
        if (y == fa || y == son[x])
            continue;
        f[y] = p;
        p += len[y]; // 给y开头的链分配内存
        DP(y, x);
        for (int j = 1; j <= len[y]; j++) {
            f[x][j] += f[y][j - 1]; // 暴力合并
            if (f[x][j] > f[x][ans[x]] ||
                f[x][j] == f[x][ans[x]] && j < ans[x])
                ans[x] = j; // 更新答案
        }
    }
    if (f[x][ans[x]] == 1)
        ans[x] = 0; // 修正
}

int main() {
    scanf("%d", &n);
    for (int i = 1; i < n; i++) {
        int x, y;
        scanf("%d%d", &x, &y);
        e[x].push_back(y);
        e[y].push_back(x);
    }
    dfs(1, 0);
    f[1] = p;
    p += len[1]; // 给树根长链分配内存
    DP(1, 0);
    for (int i = 1; i <= n; ++i)
        printf("%d\n", ans[i]);
    return 0;
}
```



## 2.5 动态规划类✅️

#### 2.5.1 最长公共子序列

```cpp
#include <bits/stdc++.h>
#define int long long 
#define endl "\n"
using namespace std;
const int N=1e3+5;
const int M=1e17;

int dp[N][N];
int flag[N][N];
string s,t;

int lcs(string s,string t){
    memset(dp,0,sizeof(dp));
    memset(flag,0,sizeof(flag));
    int n=s.size();
    int n1=t.size();
    
    for (int i=1;i<=n;i++){
        for (int j=1;j<=n1;j++){
            if(s[i-1]==t[j-1])dp[i][j]=dp[i-1][j-1]+1,flag[i][j]=0;
            else if(dp[i-1][j]>=dp[i][j-1]){
                dp[i][j]=dp[i-1][j],flag[i][j]=1;
            }else {
                 dp[i][j]=dp[i][j-1],flag[i][j]=-1;
            }
        }
    }
    return dp[n][n1];
    
}
void printff(int i,int j){
    if(i==0 ||j==0){
        return;
    }
    if(flag[i][j]==0){
        printff(i-1,j-1);
        cout<<s[i-1];
    }else if(flag[i][j]==1){
        printff(i-1,j);
    }else {
        printff(i,j-1);
    }
    
}

signed main(){
    ios::sync_with_stdio(0);cin.tie(0);cout.tie(0);
    int m;
    cin>>m;
    while(m--){
        
        cin>>s>>t;
        cout<<lcs(s,t)<<endl;
        printff(s.size(),t.size());
        cout<<endl;
    }
    
}

```

#### 2.5.2树形dp

```cpp
#include <iostream>
#include <string.h>
using namespace std;
const int max_n = 2e5+5;
const int min_r = -128;
const int max_r = 127;

int n, u, v;
int happy[max_n + 1];
int in[max_n + 1];
//链式前向星
struct edge { int v, next; }edges[max_n + 1];
int head[max_n + 1];
int tot = -1;
//树形DP
long long dp[max_n + 1][2];


//存边
void add_edge(int u, int v) {
    edges[++tot] = { v,head[u] }; head[u] = tot;
}

//树形DP
void dfs(int now) {
    //参加
    dp[now][1] = happy[now];//参加，初始化为自己的快乐指数

    //不参加
    for (int i = head[now]; i != -1; i = edges[i].next) {//遍历子节点
        int v = edges[i].v;
        dfs(v);
        //返回后更新
        dp[now][0] += max(dp[v][0], dp[v][1]);//不参加，需要累加子节点来的情况
        dp[now][1] += dp[v][0];//参加，需要累加子节点不来的情况
    }
}

int main() {
    memset(head + 1, -1, sizeof(int) * max_n);
    cin >> n;
    for (int i = 1; i <= n; i++) cin >> happy[i];
    for (int i = 1; i < n; i++) {//存图
        cin >> u >> v;
        add_edge(u, v);
        in[v]++;//入度
    }

    for (int i = 1; i <= n; i++)
        if (!in[i]) {//从根节点开始
            dfs(i);
            cout << max(dp[i][0], dp[i][1]) << endl;
            break;
        }
    return 0;
}
```



## 2.6 字符串类✅️

### 2.6.1 字符串哈希

#### 字符串哈希模板

![image-20260529230225495](C:\Users\32157\AppData\Roaming\Typora\typora-user-images\image-20260529230225495.png)

#### 字符串哈希代码

```cpp
#include <bits/stdc++.h>
#define ull unsigned long long
using namespace std;

const int N = 100010;
const int P = 131; // 13331

ull h[N], p[N];

ull get(int l, int r) {
    return h[r] - h[l - 1] * p[r - l + 1];
}

int main() {
    string s;
    cin >> s;
    int len = s.length();
    
    p[0] = 1;
    for (int i = 1; i <= len; i++) {
        h[i] = h[i - 1] * P + s[i - 1] - 'a' + 1; // 存每一位的哈希值
        p[i] = p[i - 1] * P;
    }
    
    // 如果是判断一个区间里面的字符串
    int l1, l2, r1, r2;
    cin >> l1 >> l2 >> r1 >> r2;
    
    if (get(l1, r1) == get(l2, r2))
        cout << "Yes" << endl;
    else
        cout << "No" << endl;
    
    return 0;
}
```



### 2.6.2 字典树

#### 字典树

题目描述

![page image](E:/桌面/acm相关/模板/模板_assets/page_342_298.png)

输入格式

本题单测试点内有多组测试数据。

输入的第一行是一个整数，表示数据组数 T。 对于每组数据，格式如下： 第一行是两个整数，分别表示模式串的个数 n和询问的个数 q。 接下来 n行，每行一个字符串，表示一个模式串。 接下来 q行，每行一个字符串，表示一次询问。

输出格式

按照输入的顺序依次输出各测试数据的答案。 对于每次询问，输出一行一个整数表示答案。

输入输出样例 #1

输入 #1

```cpp
3
3 3
fusufusu
fusu
anguei
fusu
anguei
kkksc
5 2
fusu
Fusu
AFakeFusu
afakefusu
fusuisnotfake
Fusu
fusu
1 1
998244353
9
```

输出 #1

```cpp
2
1
0
1
2
1
```

说明/提示

![page image](E:/桌面/acm相关/模板/模板_assets/page_343_299.png)

说明

```cpp
std 的 IO 使用的是关闭同步后的 cin/cout，本题不卡常。
```

代码

```cpp
#include <bits/stdc++.h>
#define ll long long
#define endl "\n"
using namespace std;

struct node {
    int cnt = 0;
    map<char, node*> next;
};

int main()
{
    int t;
    cin >> t;
    while (t--)
    {
        int n, q;
        cin >> n >> q;
        node* start = new node;
        node* now;
        string s;

        for (int i = 0; i < n; i++)
        {
            cin >> s;
            now = start;
            for (auto x : s)
            {
                if (now->next.find(x) == now->next.end())
                    now->next[x] = new node;
                now = now->next[x];
                now->cnt++;
            }
        }

        while (q--)
        {
            cin >> s;
            now = start;
            int ans = 0;
            for (auto x : s)
            {
                if (now->next.find(x) == now->next.end())
                {
                    ans = 0;
                    break;
                }
                else
                {
                    now = now->next[x];
                    ans = now->cnt;
                }
            }
            cout << ans << endl;
        }
    }
    return 0;
}
```

### 2.6.3 KMP

#### KMP模板

KMP 用于匹配模式串 `p` 在主串 `s` 中出现的次数以及位置。

`next` 数组表示模式串 `P[1, i]` 中相等前后缀的最长长度。

匹配过程中使用双指针，一个 `i` 指向主串，一个 `j` 指向模式串。

当模式串与主串不匹配时，`j` 回到 `next[j]`（即能继续匹配的位置），`i` 不动。

#### KMP代码

```cpp
#include <bits/stdc++.h>
#define ll long long
#define endl "\n"
using namespace std;

int Next[1000000 + 5];

// 初始化 next 数组
void getNext(string s)
{
    Next[0] = 0;
    Next[1] = 0;
    for (int i = 1; i < s.length(); i++) {
        int j = Next[i];
        while (j && s[i] != s[j]) j = Next[j];
        if (s[i] == s[j]) Next[i + 1] = j + 1;
        else Next[i + 1] = 0;
    }
}

// 匹配
void KMP(string s, string t)
{
    getNext(t);
    int j = 0;
    for (int i = 0; i < s.length(); i++) {
        while (j && s[i] != t[j]) j = Next[j];
        if (s[i] == t[j]) j++;
        if (j == t.length()) {
            cout << (i + 2 - t.length()) << endl;
            j = Next[j];
        }
    }
}

int main()
{
    string s, t;
    cin >> s >> t;
    KMP(s, t);
    for (int i = 0; i < t.length(); i++) cout << Next[i + 1] << " ";
    cout << endl;
}
```

### 2.6.4 manacher

#### manacher模板

Manacher 的作用就是在 O(N) 的时间复杂度下求出以每个位置为回文中心的最长回文半径。 Manacher 的核心思想就是尽可能借助之前已知的回文串，来减少以当前点为回文中心向两侧扩展的 操作次数

#### manacher代码

```cpp
#include <bits/stdc++.h>
#define ll long long
using namespace std;
const ll N = 11000000+1;
ll p[N*2+5];
ll manacher(string s)
{
    ll r = 0, c, n = s.length();
    for(ll i = 1; i < n; i++){
        if(i < r)p[i] = min(p[2*c-i], r-i);
        else p[i] = 1;
        while(s[i+p[i]] == s[i-p[i]])p[i]++;
        if(p[i]+i > r){
            r = p[i]+i;
            c = i;
        }
    }
    return *max_element(p, p+s.length())-1;
}
int main()
{
    string s = "$#", a;
    cin >> a;
    for(ll i = 0; i < a.length(); i++){
        s += a[i];
        s += "#";
    }
    s += "*";
    cout << manacher(s) << endl;
}
```

# 



## 2.7 杂项 ✅️

### 2.7.1 快速幂，逆元，排列组合C&&A, gcd , lcm , 判断素数,进制转换

```c++
#include <bits/stdc++.h>
#define int long long 
#define endl "\n"
using namespace std;
const int N=1e4+5;
const int M=1e10;

int fac[2*M]; // 存储预先计算的阶乘值，模M

// 初始化fac数组，计算0到2*M-1的阶乘值，并对每个值进行模M操作
void init() {
    fac[0] = 1;
     for (int i = 1; i < 2*M; i++)
         fac[i] = fac[i - 1] * i % M;
}

// 快速幂函数，计算x^y % M
int ksm(int x, int y) {
    int ans = 1;
     while (y) {
        if (y & 1)
             ans = ans * x % M;
         x = x * x % M; // 平方
         y >>= 1; // 右移一位，等同于除以2
    }
     return ans;
}

// 逆元函数，利用费马小定理计算模M下的逆元
// 它允许我们在模 m 的条件下进行除法运算。
// 由于直接除法可能不适用（因为模运算下除法不总是有定义的）
// 我们可以通过乘以逆元来间接实现除法。
int inv(int z) {
    return ksm(z, M - 2);
}

// 组合数函数，计算C(n, m) = n! / (m! * (n-m)!) % M
int C(int n, int m) {
    if (m > n) return 0;
    return fac[n] * inv(fac[m]) % M * inv(fac[n - m]) % M;
}

// 排列数函数，计算A(n, m) = n! / (n-m)! % M
int A(int n, int m) {
    if (m > n) return 0;
    return fac[n] * inv(fac[n - m]) % M;
}

int f(int n) {     //朴素算阶乘
    int result = 1;
    for (int i = 2; i <= n; ++i) {
        result *= i; 
    }
    return result;
}

int C(int n,int m){  //朴素算组合数
    return f(n)/(f(m)*f(n-m));
}


int gcd(int a, int b){
	if (a % b == 0)  return b;
	else  return gcd(b, a % b);
}

int lcm(int a, int b){
	return a / gcd(a, b) * b;
}

bool isPrime(int num) {
    if (num <= 1) return false;  // 1 和负数不是素数
    if (num == 2) return true;   // 2 是素数
    if (num % 2 == 0) return false;  // 2 以外的偶数不是素数
    // 对于大于 2 的奇数，检查是否能被其他奇数整除
    for (int i = 3; i * i <= num; i += 2) {
        if (num % i == 0) {
            return false;  // 如果能被 i 整除，则不是素数
        }
    }
    return true;  // 如果没有找到能整除的数，则是素数
}

string toBase(int n, int k) {
    string digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    string num;
    while (n > 0) {
        int temp = n % k;
        num = digits[temp] + num;
        n /= k;
    }
    return num;
}

signed main(){
    ios::sync_with_stdio(0);cin.tie(0);cout.tie(0);
   
}

```



### 2.7.2 python日期处理函数

**造日期**：`datetime(y,m,d)`     **推天数**：`timedelta(days=)`

**算差值**：`相减 .days`                 **看星期**：`weekday()`

**查闰年**：`isleap()`                    **数天数**：`monthrange()[1]`

```python
from datetime import datetime, timedelta
import calendar
d1 = datetime(2025, 1, 1)         # 1. 创建日期
d2 = d1 + timedelta(days=3)    # 2. 加3天
print((d2 - d1).days)           # 3. 算差值
print(d1.weekday())            # 4. 星期
print(calendar.isleap(2024))       # 5. 闰年
print(calendar.monthrange(2024,2)[1]) # 6. 当月天数
```



### 2.7.3 函数杂项

#### 1 优化类

```cpp
// #pragma GCC optimize (2)
// #pragma G++ optimize (2) // 手动开O2
```

#### 2 字符类

![page image](E:/桌面/acm相关/模板/模板_assets/page_024_033.png)

#### 3 数学类

```cpp
反余弦 acos
反正弦 asin
反正切 atan
反正切2 atan2
余弦 cos
正弦 sin
正切 tan
双曲余弦 cosh
双曲正弦 sinh
双曲正切 tanh
指数函数 exp
指数分解函数 frexp
乘积指数函数 fdexp
自然对数 log
以10为底的对数 log10
浮点数分解函数 modf
幂函数 pow
平方根函数 sqrt
求下限接近整数 ceil
绝对值 fabs
求上限接近整数 floor
求余数 fmod
```

#### 4 字符串类

```cpp
字符串拷贝 块拷贝(目的和源存储区不可重叠) memcpy
块拷贝(目的和源存储区可重叠) memmove
串拷贝 strcpy
按长度的串拷贝 strncpy
字符串连接函数 串连接 strcat
按长度连接字符串 strncat
串比较函数 块比较 memcmp
字符串比较 strcmp
字符串比较(用于非英文字符) strcoll
长度对字符串比较 strncmp
字符串转换 strxfrm
字符与字符串查找 字符查找 memchr
字符查找 strchr
字符串查找 strcspn
字符串查找 strpbrk
字符串查找 strspn
字符串查找 strstr
字符串分解 strtok
杂类函数 字符串设置 memset
错误字符串映射 strerror
求字符串长度 strlen
```

字符串转换函数

```cpp
字符串转换为整数 atoi
字符串转换为长整数 atol
字符串转换为浮点数 strtod
字符串转换为长整数 strtol
字符串转换为无符号长整型 strtoul
```

#### 5 进制转换

```
#include <bits/stdc++.h>
const int N = 1e5 + 3;
int n, m, x, tmp, ansl;
char a[N], ans[N];
inline int n_to_ten()
{
    int x = 0;
    for (int i = 0; a[i]; i++)
    {
        x *= n;
        if (a[i]≥'A' & a[i]≤'F')
            x += (a[i] - 'A' + 10);
        else
            x += (a[i] - '0');
    }
    return x;
}
inline void ten_to_m()
{
    do {
        tmp = x % m;
        if (tmp < 10)
            ans[++ansl] = '0' + tmp;
        else
            ans[++ansl] = 'A' + tmp - 10;
        x /= m;
    } while (x);
}
int main()
{
    scanf("%d%s%d", &n, a, &m);
    x = n_to_ten();
    ten_to_m();
    for (int i = ansl; i; --i)
        printf("%c", ans[i]);
    puts("")
}
```

# 三 、经验环节

推理与猜测题目

### 3.1 算法竞赛中时间复杂度、数据范围与时间限制 的关系

![page image](E:/桌面/acm相关/模板/模板_assets/page_022_030.png)

### 3.2 由数据范围反推算法复杂度以及算法内容

![page image](E:/桌面/acm相关/模板/模板_assets/page_022_031.png)

![page image](E:/桌面/acm相关/模板/模板_assets/page_023_032.png)

# 
