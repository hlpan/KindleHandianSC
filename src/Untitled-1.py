import pygame.freetype
import pygame.surface
import pygame
pygame.freetype.init()
font = pygame.freetype.Font('big_font_heiti/SourceHanSansSC-Medium.otf', 50)
surf=pygame.Surface((50,50))
surf.fill((255,255,255))

word='中'
#font.origin = True
width, height = surf.get_size()
bounds = font.get_rect(word)

x,y=(width-bounds.width)/2,(height-bounds.height)/2

if x>0 and y>0 :
    font.render_to(surf, (x, 0), word, (0,0,0),(255,255,255))
    pygame.image.save(surf,'1.jpeg')
else:
    surf1,textpos=font.render(word, (0,0,0))
    pygame.image.save(surf1,'1.jpeg')
