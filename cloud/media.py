"""Bounded media inspection. Descriptive metadata is not a scientific verdict."""
import io
import tempfile
from pathlib import Path
from PIL import Image, UnidentifiedImageError


def inspect_media(data, name, kind):
    suffix=Path(name).suffix.lower()
    if kind=='photo':
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {'JPEG','PNG'} or image.width*image.height>40_000_000:
                    raise ValueError('Use JPEG/PNG up to 40 megapixels')
                result={'kind':'image','format':image.format,'width':image.width,'height':image.height,
                        'inspection':'image_structure','scientific_content_assessed':False}
                image.verify()
            return result
        except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
            raise ValueError('Invalid JPEG or PNG image') from exc
    if kind=='video':
        if suffix!='.mp4' or len(data)<12 or data[4:8]!=b'ftyp':
            raise ValueError('Use an MP4 video')
        import cv2
        with tempfile.TemporaryDirectory(prefix='nocap-video-') as folder:
            path=Path(folder)/'capture.mp4';path.write_bytes(data)
            cap=cv2.VideoCapture(str(path))
            try:
                width,height=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if not cap.isOpened() or not 0<width*height<=40_000_000:
                    raise ValueError('MP4 video could not be decoded')
                ok,frame=cap.read()
                if not ok: raise ValueError('MP4 contains no decodable first frame')
                return {'kind':'video','format':'MP4','width':width,'height':height,
                        'inspection':'first_frame_decoded','scientific_content_assessed':False}
            finally: cap.release()
    return {'kind':kind,'inspection':'hash_only','scientific_content_assessed':False}
