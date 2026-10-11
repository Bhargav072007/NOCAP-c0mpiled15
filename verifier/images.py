"""Hash equality and conservative resize/crop similarity; never forensic proof."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
import imagehash
from .provenance import sha256_file

class ImageError(ValueError): pass

def load_image(path):
    try:
        with Image.open(path) as raw:
            if raw.width*raw.height>30_000_000: raise ImageError('Image exceeds pixel limit')
            return ImageOps.exif_transpose(raw).convert('RGB')
    except (OSError,Image.DecompressionBombError) as exc: raise ImageError('Invalid/oversized image') from exc

def similarity(path_a,path_b, *, crop=None):
    a=load_image(path_a);b=load_image(path_b)
    if sha256_file(path_a)==sha256_file(path_b):
        return {'kind':'exact_hash','distance':0,'similarity':1.0,'transformed':False}
    if crop is not None:
        if len(crop)!=4 or any(type(x) not in (int,float) or not 0<=x<=1 for x in crop): raise ImageError('Crop must be normalized [left,top,right,bottom]')
        if crop[0]>=crop[2] or crop[1]>=crop[3]: raise ImageError('Empty crop')
        b=b.crop(tuple(int(x*s) for x,s in zip(crop,(b.width,b.height,b.width,b.height))))
    distance=int(imagehash.phash(a)-imagehash.phash(b))
    # Pixel comparison helps detect perceptual-hash collisions, especially uniform panels.
    aa=np.asarray(a.resize((64,64),Image.Resampling.LANCZOS)).astype(float)
    bb=np.asarray(b.resize((64,64),Image.Resampling.LANCZOS)).astype(float)
    mae=float(np.mean(np.abs(aa-bb))/255)
    if distance<=6 and mae<=.06:
        kind='crop_or_resize_similar' if crop else 'resize_similar'
    else:
        kind='different'
        if crop is None:
            located=locate_crop(a,b)
            if located:
                return {'kind':'automatic_crop_similar','distance':distance,'pixel_mae':located['pixel_mae'],
                        'similarity':located['inlier_ratio'],'transformed':True,'crop_proposal':located}
    return {'kind':kind,'distance':distance,'pixel_mae':mae,'similarity':max(0,1-distance/64),'transformed':True}

def possible_reuse(figures):
    matches=[]
    for i,a in enumerate(figures):
        for b in figures[i+1:]:
            try: hit=similarity(a['path'],b['path'])
            except (ImageError,OSError): continue
            if hit['kind']!='different' and a.get('condition') and b.get('condition') and a['condition']!=b['condition']:
                matches.append({'first':a['id'],'second':b['id'],'comparison':hit})
    return matches

def locate_crop(query,original):
    """Propose an affine crop match with feature geometry; requires human review."""
    import cv2
    a=query.copy();b=original.copy();a.thumbnail((1200,1200));b.thumbnail((1200,1200))
    gray_a=cv2.cvtColor(np.array(a),cv2.COLOR_RGB2GRAY)
    gray_b=cv2.cvtColor(np.array(b),cv2.COLOR_RGB2GRAY)
    orb=cv2.ORB_create(nfeatures=1800)
    ka,da=orb.detectAndCompute(gray_a,None);kb,db=orb.detectAndCompute(gray_b,None)
    if da is None or db is None or len(ka)<12 or len(kb)<12: return None
    pairs=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2)
    good=[m for pair in pairs if len(pair)==2 for m,n in [pair] if m.distance<.7*n.distance]
    if len(good)<12: return None
    qa=np.float32([ka[m.queryIdx].pt for m in good]);ob=np.float32([kb[m.trainIdx].pt for m in good])
    matrix,inliers=cv2.estimateAffinePartial2D(qa,ob,method=cv2.RANSAC,ransacReprojThreshold=3)
    if matrix is None or inliers is None or int(inliers.sum())<12 or float(inliers.mean())<.75: return None
    corners=np.array([[0,0],[a.width,0],[a.width,a.height],[0,a.height]],dtype=np.float32)
    mapped=cv2.transform(corners[None,:,:],matrix)[0]
    left,top=np.min(mapped,axis=0);right,bottom=np.max(mapped,axis=0)
    if left< -3 or top< -3 or right>b.width+3 or bottom>b.height+3: return None
    area=(right-left)*(bottom-top)/(b.width*b.height)
    if not .05<=area<.98: return None
    crop=[float(max(0,left)/b.width),float(max(0,top)/b.height),float(min(b.width,right)/b.width),float(min(b.height,bottom)/b.height)]
    box=tuple(int(x*s) for x,s in zip(crop,(original.width,original.height,original.width,original.height)))
    target=original.crop(box)
    aa=np.asarray(query.resize((64,64),Image.Resampling.LANCZOS)).astype(float)
    bb=np.asarray(target.resize((64,64),Image.Resampling.LANCZOS)).astype(float)
    mae=float(np.mean(np.abs(aa-bb))/255)
    if mae>.08: return None
    return {'crop':crop,'inliers':int(inliers.sum()),'inlier_ratio':float(inliers.mean()),'pixel_mae':mae}
