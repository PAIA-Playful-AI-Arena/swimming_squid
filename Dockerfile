FROM paiatech/paia-game-env:20250525

ADD . /game
WORKDIR /game

CMD ["bash"]
