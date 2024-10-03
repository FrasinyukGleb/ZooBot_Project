import json

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from aiogram import F

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Router, types
from random import sample

from questions import QUESTIONS, ANIMALS

router = Router()


class Quiz(StatesGroup):
    quest = State()
    feedback = State()
    text_to_stuff = State()

    quiz_result = State()
    questions = State()


amphibian_list = [x['answers'][0] for x in QUESTIONS]
reptile_list = [x['answers'][1] for x in QUESTIONS]
mammal_list = [x['answers'][2] for x in QUESTIONS]
bird_list = [x['answers'][3] for x in QUESTIONS]
check_list = amphibian_list + reptile_list + mammal_list + bird_list
check_list.append('Начать')


@router.message(Quiz.quest)
async def make_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    quiz_result, questions = data['quiz_result'], data['questions']

    if message.text not in check_list:
        await message.answer(f'Не понимаю 🙈\nПожалуйста, выбери ответ из предложенных вариантов или введи "Начать"')
        return


    if message.text in amphibian_list:
        quiz_result['amphibian'] += 1
    elif message.text in reptile_list:
        quiz_result['reptile'] += 1
    elif message.text in mammal_list:
        quiz_result['mammal'] += 1
    elif message.text in bird_list:
        quiz_result['bird'] += 1
    await state.update_data({'quiz_result': quiz_result})


    if not questions:
        await state.clear()
        win_category = max(quiz_result, key=quiz_result.get)
        for category, animals in ANIMALS.items():
            if category == win_category:
                win_animal = sample(animals, 1)[0]

                result_message = f'🫧 Вы можете стать опекуном этого милого создания и частью большого круга друзей Московского зоопарка\n' \
                                 f'🐾 Ваш возможный подопечный: <a href="{win_animal["url"]}">{win_animal["name"]}</a> 🐾 \n\n' \
                                 f'🫧 Подробнее о программе опекунства: ' \
                                 f'<a href="https://moscowzoo.ru/about/guardianship">«Клуб друзей зоопарка»</a>'

                await state.set_data({'result_name': win_animal['name']})
                kb = [
                        [InlineKeyboardButton(text='Попробовать ещё раз?', callback_data='replay')],
                        [InlineKeyboardButton(text='Связаться с сотрудником Зоопарка', callback_data='contact')],
                        [InlineKeyboardButton(text='Поделиться в VK', callback_data='replay',
                                              url=f'https://vk.com/share.php?url={win_animal["url"]}'
                                                  f'&title=@totem_zoo_bot\nТвоё тотемное животное: {win_animal["name"]}'
                                                  f'&image={win_animal["photo"]}',)],
                        [InlineKeyboardButton(text='Оставить отзыв', callback_data='feedback')]
                ]
                inlinekb = InlineKeyboardMarkup(inline_keyboard=kb)

                await message.answer(f'Ура! Викторина закончена! \n'
                                     f'Твоё тотемное животное: {win_animal["name"]}',
                                     reply_markup=types.ReplyKeyboardRemove())
                await message.answer_photo(photo=win_animal['photo'])

                await message.answer(result_message, parse_mode='HTML', reply_markup=inlinekb)

                return

    question = sample(questions, 1)[0]
    questions.pop(questions.index(question))
    variants = question['answers']
    await state.update_data({'questions': questions})

    builder = ReplyKeyboardBuilder()
    for _ in variants:
        builder.add(types.KeyboardButton(text=_))
    builder.adjust(2)

    await message.answer(f"{question['question']}", reply_markup=builder.as_markup(resize_keyboard=True))


@router.callback_query(F.data == 'replay')
async def replay(callback: types.CallbackQuery, state: FSMContext):
    await state.set_data(
        {'quiz_result': {
            'amphibian': 0,
            'reptile': 0,
            'mammal': 0,
            'bird': 0},
            'questions': QUESTIONS.copy()
        }
    )

    await state.set_state(Quiz.quest.state)
    kb = [[types.KeyboardButton(text='Начать')]]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True
    )
    await callback.message.answer(f'Начнём?', reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == 'contact')
async def contact(callback: types.CallbackQuery, state: FSMContext):
    result_name = await state.get_data()
    buttons = [[types.KeyboardButton(text=f'🦉 Чат с сотрудником 🦉\n '
                                          f'Результат викторины: \n{result_name["result_name"]}')]]
    kb = types.ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    await callback.message.answer(f'Чтобы узнать больше о программе опекунства, '
                                  f'Вы можете связаться с нашим сотрудником Глебом: \n\n'
                                  f'✏   Telegram: @ххх\n'
                                  f'✉   E-mail: ххх@хх.хх\n'
                                  f'📞   +7-9хх-ххх-хх-хх', reply_markup=kb)
    await state.set_state(Quiz.text_to_stuff.state)
    await callback.answer()


@router.message(Quiz.text_to_stuff) #Для корректной работы необходимо указать chat_id чата с сотрудником
async def text_to_stuff(message: types.Message, state: FSMContext):
    await message.copy_to(chat_id='хххххххххх', reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@router.callback_query(F.data == 'feedback')
async def feedback_state(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Quiz.feedback.state)
    await callback.message.answer(
        f'🫧 Напишите свои впечатления о нашем боте или свои предложения по его улучшению. \n\n'
        f'А мы постараемся сделать его удобнее для Вас 🐻‍❄')
    await callback.answer()


@router.message(Quiz.feedback)
async def feedback_add(message: types.Message, state: FSMContext):
    with open('feedbacks.json', 'r', encoding='utf8') as fb_file:
        fb = json.load(fb_file)
        with open('feedbacks.json', 'w', encoding='utf8') as new_fb_file:
            new = {
                'feedback': message.text,
                'user': message.from_user.username
            }
            fb.append(new)
            new_data = json.dumps(fb, indent=4, ensure_ascii=False)
            new_fb_file.write(new_data)

    await message.answer(f'Спасибо за Ваш отзыв! 🦉')
    await state.clear()
