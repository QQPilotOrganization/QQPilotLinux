

import cv2
import numpy
from numpy import  ndarray
def FindTemplates(imagePath,templatePath,tolerance=30,maxCount=1):
    image=cv2.imread(imagePath,0)
    template=cv2.imread(templatePath,0)
    assert(isinstance(image,ndarray))
    assert(isinstance(template,ndarray))

    
    w, h = template.shape[::-1]
    # if image==None or template==None:
    #     return []
    threshold=(100-tolerance)/100
    res=cv2.matchTemplate(image,template,cv2.TM_CCOEFF_NORMED)
    loc = numpy.where(res >= threshold)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res) 
    # top_left = max_loc  # 假设使用的是归一化相关系数匹配方法
    # bottom_right = (top_left[0] + template.shape[1], top_left[1] + template.shape[0])
    # image=cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)
    # cv2.rectangle(image, top_left, bottom_right, (0, 0, 255), 2)  # 标注矩形框
    # cv2.imshow('Matched Image', image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    f=[]
    for pt in zip(*loc[::-1]):
        f.append([int(pt[0]),int(pt[1])])
    return f[:maxCount]
        


if __name__=="__main__":
    print(FindTemplates('test1.png','uploadImage.png',30,99999))