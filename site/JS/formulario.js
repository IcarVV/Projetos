class FormSubmit { 

    constructor(settings) {
        this.settings = settings;
        this.form = document.querySelector(settings.form);
        this.formButton = document.querySelector(settings.button);

        if (this.form) {
            this.url = this.form.getAttribute('action');
        }
        this.sendForm = this.sendForm.bind(this);
    }


    displaySuccess(){
        this.form.innerHTML = this.settings.success;
    }

    displayError(){
        this.form.innerHTML = this.settings.error;
    }

    getFormObject() {

        const formObject = {};
        const fields = this.form.querySelectorAll('[name]');
        fields.forEach((field) => {
            formObject[field.getAttribute('name')] = field.value;
        });
        return formObject;

    }

    onSumission(event) {

        event.preventDefault(); // impede reload
        event.target.disabled = true; // desabilita o botão
        event.target.innerText = 'Enviando...'; // muda o texto do botão
    }

    async sendForm(event) {
        event.preventDefault();

        const button = this.form.querySelector('[data-button]');
        button.disabled = true;
        button.innerText = 'Enviando...';

        try {
        const formData = new FormData(this.form);

            const response = await fetch(this.url, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error();

            this.displaySuccess();
        
        }   catch (error) {
            this.displayError();
        }
    }

    init() {

        if (this.form) {
            this.formButton.addEventListener('click', this.sendForm);
        }
        return this;
    
    }   

}

const formSubmit = new FormSubmit({
    form: '[data-form]',
    button: '[data-button]',
    success: '<h1 class="success">Mensagem enviada com sucesso!</h1>' + '<p class="success">Em breve entrarei em contato.</p>',
    error: '<h1 class="error">Não foi possivel fazer o envio da mensagem.</h1>'
});

formSubmit.init();