import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

card = KoikatuCharaData.load(
    'C:/Games/Koikatsu/UserData/chara/female/kkRenderBridge/MartaLorente.png')
card.Parameter.data['bloodType'] = 0  # O
card.save('C:/Games/Koikatsu/UserData/chara/female/kkRenderBridge/MartaLorente.png')
print('Fixed bloodType=0 (O) on MartaLorente.png')
print(f'Verify: {card.Parameter.data["bloodType"]}')
