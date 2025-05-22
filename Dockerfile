FROM paiatech/paia-game-env:20250522
ADD . /game
WORKDIR /game
RUN pip install -r requirements.txt --no-cache-dir
CMD ["bash"]
