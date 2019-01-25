# -*- coding: UTF-8 -*-

from PIL import Image
import random
import os
class Png2Gif:
    def convert(self, png_file):
        png_image=Image.open(png_file).convert('LA')
        threshold = 0
        gray,alpha=png_image.split()
        gray=Image.eval(alpha, lambda px: 255-px)
        alpha=Image.eval(alpha, lambda px: 255 if px >=1 else 0)
        colour = self.unique_color(gray)
        gray.paste(colour, mask=alpha)
        

        png_image.paste(gray, mask=alpha)
        png_image=gray.convert('P', palette=Image.ADAPTIVE)
        new_name=os.path.splitext(png_file)[0]+'.gif'
        png_image.save(new_name, transparency=self.color_index(png_image, colour))
        return new_name
    def unique_color(self, image):
        """find a color that doesn't exist in the image
        """
        colors = image.getdata()
        while True:
            # Generate a random color
            color = random.randint(0, 255)
    
            if color not in colors:
                return color

    def fill_transparent(self, image, color, threshold=0): 
        """Fill transparent image parts with the specified color 
        """
        def quantize_and_invert(alpha):
            if alpha <= threshold:
                return 255
            return 0
        # Get the alpha band from the image
    
            gray, alpha = image.split()
        # Set all pixel values below the given threshold to 255,
        # and the rest to 0
        alpha = Image.eval(alpha, quantize_and_invert)
        # Paste the color into the image using alpha as a mask
        image.paste(color, mask=alpha)
    def color_index(self, image, color):
        """Find the color index
        """
        palette=image.getpalette()
        index=palette.index(color)
        return index

pg=Png2Gif()
pg.convert('1.png')