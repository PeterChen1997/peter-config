# Theme Powerlevel10k
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# neovim
alias vim='nvim'
alias vi='nvim'

# nvm
export NVM_DIR="$HOME/.nvm"
[ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && . "/opt/homebrew/opt/nvm/nvm.sh"                                       # This loads nvm
[ -s "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm" ] && . "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm" # This loads nvm bash_completion

# yarn
export PATH="$PATH:$(yarn global bin)"

# homebrew
export PATH="/opt/homebrew/bin:$PATH"

# rbenv
eval "$(rbenv init -)"

# pnpm
export PNPM_HOME="$HOME/Library/pnpm"
export PATH="$PNPM_HOME:$PATH"

# zsh
plugins=(git zsh-autosuggestions zsh-syntax-highlighting autojump copypath copyfile)
ZSH_THEME="powerlevel10k/powerlevel10k"
export ZSH=~/.oh-my-zsh
source $ZSH/oh-my-zsh.sh
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# zplug
export ZPLUG_HOME=/opt/homebrew/opt/zplug
source $ZPLUG_HOME/init.zsh

# extra pkgs
export PATH=$HOME/.meteor:$PATH
export PATH=$HOME/Downloads/qshell:$PATH

# alias
alias zj='zellij'

# pyenv
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# deno
export DENO_INSTALL="$HOME/.deno"
export PATH="$DENO_INSTALL/bin:$PATH"

# git
alias m="make -f $HOME/config/git.mk"
