import requests
from bs4 import BeautifulSoup
import pymysql
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
import numpy  as np
import pandas as pd
from sqlalchemy import create_engine , text
from urllib.parse import quote_plus

"""
爬取内容为当日（实时）企业基金数据。
以下是其url:https://www.dayfund.cn/dayvalue.html
"""

#这是请求头部分，起dic为名以防止和后续表头信息存储变量重名
dit = {"referer": "https://www.dayfund.cn/incrank.html"
  ,
       "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"}
#没找到合适的ip代理，有的话可以加上
proxies = {
  None
}
#用以暂时存储读取数据
df_list = []
#用以记录清洗后的数据
df_list_pd=pd.DataFrame()
#后续要进行数据清洗，手动填写了表头内容，否则可直接使用39-41行代码
headers = ['序号', '基金代码', '基金名称', '日增长(%)', '近1周(%)', '近1月(%)', '近1季(%)', '近半年(%)', '今年来(%)', '近1年(%)',
                   '近2年(%)','近3年(%)']
#这是我的爬虫函数，用以爬取数据并储存
def download_one_page(index, url):
   try:
      req = requests.get(url=url, headers=dit, timeout=(3, 10),verify=True)#timeout用以延长访问间隔
      soup = BeautifulSoup(req.text, "html.parser")
      table = soup.find_all("tr", class_=["row1", "row2"])

      # header_row = soup.find('tr', class_='rowh')
      # if header_row:
      #   headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]# 这步骤可要可不要


      for row in table:
        cells = row.find_all('td')
        row_data = [cell.get_text(strip=True) for cell in cells]

        # 如果表头存在且长度匹配，则将行数据与表头组合成字典
        if len(row_data) == len(headers):
          row_dict = dict(zip(headers, row_data))
          df_list.append(row_dict)
          # 如果长度不匹配，可能是不需要的数据或表格结构变化
        else:
            print(f"Row data length mismatch on page {index}: {row_data}")
      print(f"第{index}页爬取完成")
      time.sleep(random.uniform(1, 3))  # 设置随机延时，如若频繁请求可能触发网站反爬机制

   except Exception as en:
       print(f"第{index}页爬取失败: {str(en)}")


#显而易见，这是一个数据清洗函数，用以处理“-0.07%”样式的数字为浮点数
def wash_data_pd(a):
      list_pd = pd.DataFrame(a,columns = headers)
      numeric_columns = headers[headers.index('日增长(%)'):]
      for col in numeric_columns:
              list_pd[col] = list_pd[col].replace('-', np.nan)
              list_pd[col] = list_pd[col].str.replace('%', '', regex=False).astype(float)
      return list_pd


#这是我的数据写入函数，用以将清洗后的数据写入数据库
def save_to_mysql(data_list_pd):
    if data_list_pd.empty:
        print("没有数据可保存，数据列表为空")
        return
    try:
        #这是因为我的密码中有“@”，需要进行编码
        encoded_password = quote_plus('liu@423615')#将“@”编码为"%40"
        #连接到自建数据库
        engine = create_engine(f'mysql+pymysql://root:{encoded_password}@localhost:3306/spider_database')
        with engine.connect() as conn:
            #可以用ctrl+alt+L来解决缩进问题
            create_table_query = text("""
                                      CREATE TABLE IF NOT EXISTS dayfund_spider_data
                                      (
                                          id           INT AUTO_INCREMENT PRIMARY KEY,
                                          `序号`       int NOT NULL,
                                          `基金代码`   VARCHAR(20),
                                          `基金名称`   VARCHAR(100),
                                          `日增长(%)`  float,
                                          `近1周(%)`   float,
                                          `近1月(%)`   float,
                                          `近1季(%)`   float,
                                          `近半年(%)`  float,
                                          `今年来(%)`  float,
                                          `近1年(%)`   float,
                                          `近2年(%)`   float,
                                          `近3年(%)`   float,
                                          `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                      )
                                      """)

            conn.execute(create_table_query)
            conn.commit()

        if not data_list_pd.empty:
            data_list_pd.to_sql('dayfund_spider_data', con=engine, if_exists='replace', index=False)
            print(f"成功插入 {len(data_list_pd)} 条记录到spider_database数据库")
        else:
            print("准备插入的记录列表为空，跳过插入操作")
        engine.dispose()#记得需要手动关闭连接


    except pymysql.MySQLError as pe:
            print(f"数据库错误: {str(pe)}")
    except Exception as ec:
            print(f"保存数据出错: {str(ec)}")


if __name__ == "__main__":
    # 这是想要爬取页面的范围，这个网页共有116页
    pages = range(1, 6)
    urls = [f"https://www.dayfund.cn/incrank_p{i}.html" for i in pages]

    # 使用线程池以提高运行效率，并确保所有线程完成
    with ThreadPoolExecutor(max_workers=2) as T:#此处max_workers为最大线程数
        # 提交所有任务并获取Future对象
        futures = [T.submit(download_one_page, i, url) for i, url in enumerate(urls,start=1)]

        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                future.result()  # 获取结果（如果有异常会在这里抛出）
            except Exception as e:
                print(f"线程执行出错: {str(e)}")

    # 所有线程完成后再保存数据
    print(f"所有页面爬取完成，共获取 {len(df_list)} 条数据，开始清洗...")

    df_list_pd=wash_data_pd(df_list)
    print("清洗完成，开始写入数据库...")

    #传入读取数据并写入数据库
    save_to_mysql(df_list_pd)
    print("数据写入完成！！！")
"""后续用异步协程方法改写‘写入数据库函数部分’以提高写入效率"""
"""也可将全部函数框架用异步协程框架改写"""











