const tutorialVideo = document.getElementById('tutorialVideo');
const tutorialPlaceholder = document.getElementById('tutorialPlaceholder');
const tutorialModal = document.getElementById('tutorialModal');
const tutorialChapters = document.getElementById('tutorialChapters');
const closeTutorialBtn = document.getElementById('closeTutorialBtn');
const tutorialBackdrop = document.getElementById('tutorialBackdrop');
const tutorialButtons = document.querySelectorAll('.tutorial-btn');

const chapters = [
  { title: '1. Create a room', text: 'Choose a display name, create a private room, and share the invite code with three friends.' },
  { title: '2. Draw and match', text: 'On your turn, draw a card and build your collection. Matching luxury brands complete a pair and score points.' },
  { title: '3. Chase the crown', text: 'Keep an eye on the leaderboard, build your best combos, and finish the round before the 15 turns run out.' },
  { title: '4. Win the league', text: 'The highest total score wins the Luxury League crown. A perfect collection and smart timing are everything.' }
];

tutorialChapters.innerHTML = chapters
  .map((chapter) => `
    <div class="chapter-item">
      <strong>${chapter.title}</strong>
      <span>${chapter.text}</span>
    </div>
  `)
  .join('');

const luxuryVideoSrc = 'https://videos.pexels.com/video-files/3195394/3195394-hd_1920_1080.mp4';

const openTutorial = () => {
  tutorialModal.classList.remove('hidden');
  document.body.classList.add('modal-open');

  if (!tutorialVideo.dataset.loaded) {
    tutorialVideo.src = luxuryVideoSrc;
    tutorialVideo.dataset.loaded = 'true';
  }

  setTimeout(() => {
    tutorialVideo.play().catch(() => {});
  }, 150);
};

const closeTutorial = () => {
  tutorialModal.classList.add('hidden');
  document.body.classList.remove('modal-open');
  tutorialVideo.pause();
  tutorialVideo.currentTime = 0;
};

tutorialButtons.forEach((button) => {
  button.addEventListener('click', openTutorial);
});

closeTutorialBtn.addEventListener('click', closeTutorial);
tutorialBackdrop.addEventListener('click', closeTutorial);

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !tutorialModal.classList.contains('hidden')) {
    closeTutorial();
  }
});

tutorialVideo.addEventListener('error', () => {
  tutorialVideo.classList.add('hidden');
  tutorialPlaceholder.classList.remove('hidden');
});

const landingVideo = document.getElementById('landingVideoPreview');
if (landingVideo) {
  landingVideo.addEventListener('ended', () => {
    landingVideo.currentTime = 0;
    landingVideo.play().catch(() => {});
  }, false);
}
