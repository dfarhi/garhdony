import tarfile

images_tarball_path = "data/forkbomb_images.tar.gz"
def unpack_images():
    with tarfile.open(images_tarball_path, "r:gz") as tar:
        tar.extractall("data/forkbomb_images")

# Now they are in silly folders like data/forkbomb_images/images/a/a3/image.png
# We want them in data/forkbomb_images/image.png
import os
import shutil
HEX_DIGITS = "0123456789abcdef"
def flatten_images():
    for first_hex_digits in HEX_DIGITS:
        for second_hex_digits in HEX_DIGITS:
            folder = f"data/forkbomb_images/images/{first_hex_digits}/{first_hex_digits}{second_hex_digits}"
            if os.path.isdir(folder):
                for file in os.listdir(folder):
                    if file.endswith(".png"):
                        shutil.move(os.path.join(folder, file), os.path.join("data/forkbomb_images", file))
    shutil.rmtree("data/forkbomb_images/images")

def unpack():
    unpack_images()
    flatten_images()
