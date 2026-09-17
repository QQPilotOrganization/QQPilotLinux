
import base64
import io
from PIL import Image
import log2


def CompressImage(base64src: str, quality: int = 60, max_width: int = 800) -> str:
    base64srcDuplicated=base64src
    try:
        if ',' in base64src:
            base64src = base64src.split(',', 1)[1]
        imageBytes = base64.b64decode(base64src)
        image=Image.open(io.BytesIO(imageBytes))
        if image.width > max_width:
            ratio = max_width / image.width
            new_size = (max_width, int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        result=io.BytesIO()
        image.save(result, format='JPEG', quality=quality, optimize=True)
        compressed = base64.b64encode(result.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{compressed}"
    except Exception as e:
        log2.LogColored("[Compres] 错误"+str(e),log2.Fore.YELLOW)
        return base64srcDuplicated